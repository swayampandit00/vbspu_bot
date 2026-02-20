from flask import Blueprint, render_template, request, jsonify, session
from database import DatabaseManager
from scraper import VBSPUScraper
import uuid
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

user_bp = Blueprint('user', __name__, template_folder='templates')

# Initialize database and scraper
db = DatabaseManager()
scraper = VBSPUScraper()

class UserVBSPUBot:
    def __init__(self):
        self.db = db
        self.scraper = scraper
        
    def get_relevant_data(self, query):
        """Get relevant data from scraped information and uploaded PDFs"""
        # Get all scraped data from database
        all_data = self.db.get_scraped_data()
        if not all_data:
            all_data = {}
        
        query = query.lower()
        relevant_info = {}
        
        # First check for relevant PDFs
        relevant_pdfs = self.db.get_relevant_pdfs(query, limit=3)
        if relevant_pdfs:
            relevant_info['pdfs'] = relevant_pdfs
        
        # Check what category the query belongs to
        if any(word in query for word in ['admission', 'admit', 'apply', 'entrance']):
            relevant_info['fees'] = all_data.get('fees', {})
        elif any(word in query for word in ['course', 'department', 'program', 'study']):
            relevant_info['courses'] = all_data.get('courses', {})
        elif any(word in query for word in ['exam', 'result', 'date', 'schedule']):
            relevant_info['examinations'] = all_data.get('examinations', {})
        elif any(word in query for word in ['fee', 'fees', 'scholarship', 'cost']):
            relevant_info['fees'] = all_data.get('fees', {})
        elif any(word in query for word in ['news', 'notice', 'announcement', 'update']):
            relevant_info['news_notices'] = all_data.get('news_notices', {})
        else:
            # Return general info with fees for default
            relevant_info = {
                'fees': all_data.get('fees', {}),
                'courses': all_data.get('courses', {})
            }
        
        # Add course detection context
        relevant_info['query'] = query
        return relevant_info
    
    def generate_pdf_response(self, pdfs, query):
        """Generate response from uploaded PDFs"""
        if not pdfs:
            return ""
        
        response = "📄 **Relevant Information from Uploaded PDFs:**\n\n"
        
        for pdf in pdfs:
            pdf_id = pdf[0]
            filename = pdf[2]
            category = pdf[3]
            tags = pdf[4]
            description = pdf[5]
            upload_date = pdf[7]
            
            response += f"📋 **{filename}** (Category: {category})\n"
            
            if description:
                response += f"• **Description**: {description}\n"
            
            if tags:
                response += f"• **Tags**: {tags}\n"
            
            response += f"• **Uploaded**: {upload_date}\n"
            
            # Get PDF content for this query
            content_results = self.db.search_pdf_content(query)
            relevant_content = [result for result in content_results if result[0] == pdf_id]
            
            if relevant_content:
                response += "• **Relevant Content**:\n"
                for content in relevant_content[:2]:  # Show top 2 relevant pages
                    page_num = content[2]
                    text = content[1]
                    # Extract relevant snippet
                    words = text.split()
                    for i, word in enumerate(words):
                        if query.lower() in word.lower():
                            start = max(0, i-5)
                            end = min(len(words), i+15)
                            snippet = ' '.join(words[start:end])
                            response += f"  - Page {page_num}: ...{snippet}...\n"
                            break
            
            response += "\n"
        
        response += "💡 **Note**: This information is from uploaded PDF documents. For official updates, please check the university website.\n"
        return response
    
    def generate_response(self, user_message, session_id=None):
        """Generate enhanced response using scraped data and uploaded PDFs"""
        user_message = user_message.strip().lower()
        
        # Get relevant scraped data and PDFs
        relevant_data = self.get_relevant_data(user_message)
        
        # Check for off-topic queries
        off_topic_keywords = ['weather', 'politics', 'sports', 'movies', 'entertainment', 'jokes']
        if any(keyword in user_message for keyword in off_topic_keywords):
            response = self.db.get_setting('off_topic_response') or "Main sirf VBSPU se related queries me hi madad kar sakta hoon."
            return response
        
        # Check for illegal/forged document requests
        illegal_keywords = ['fake', 'forged', 'illegal', 'duplicate marksheet', 'fake certificate']
        if any(keyword in user_message for keyword in illegal_keywords):
            return "Main aise illegal documents ke bare me baat nahi kar sakta. Kripya university ki official procedure follow karein."
        
        # Generate response based on query type
        response = ""
        
        # Priority 1: PDF-based responses (if available)
        if relevant_data.get('pdfs'):
            pdf_response = self.generate_pdf_response(relevant_data['pdfs'], user_message)
            if pdf_response:
                response += pdf_response + "\n"
        
        # Priority 2: Category-based responses
        if any(word in user_message for word in ['admission', 'admit', 'apply', 'entrance']):
            response += self.generate_admission_response(relevant_data)
        elif any(word in user_message for word in ['course', 'department', 'program', 'study']):
            response += self.generate_course_response(relevant_data)
        elif any(word in user_message for word in ['exam', 'result', 'date', 'schedule']):
            response += self.generate_exam_response(relevant_data)
        elif any(word in user_message for word in ['fee', 'fees', 'scholarship', 'cost']):
            response += self.generate_fee_response(relevant_data)
        elif any(word in user_message for word in ['news', 'notice', 'announcement', 'update']):
            response += self.generate_news_response(relevant_data)
        
        elif any(word in user_message for word in ['contact', 'phone', 'address', 'email']):
            return self.generate_contact_response()
        
        else:
            # Default response
            welcome_msg = self.db.get_setting('welcome_message') or "नमस्ते! मैं VBSPU AI Assistant हूं। क्या जानना चाहते हैं आप?"
            response = f"""{welcome_msg}

मैं आपको इन विषयों में मदद कर सकता हूं:

🔹 Admissions aur courses
🔹 Fees aur scholarships  
🔹 Exam dates aur results
🔹 Facilities aur campus info
🔹 News aur notices

आप क्या जानना चाहते हैं?"""
        
        return response
    
    def generate_admission_response(self, data):
        """Generate admission response using scraped data"""
        admissions = data.get('admissions', {})
        
        response = "VBSPU me admission ke liye ye information hai:\n\n"
        
        if admissions.get('undergraduate'):
            response += "🔹 **UG Admission**:\n"
            for item in admissions['undergraduate'][:3]:
                response += f"• {item.get('title', 'N/A')}\n"
        
        response += "\n🔹 **Important Points**:\n"
        response += "• Samarth portal se online apply karein\n"
        response += "• 12th pass for UG, graduation for PG\n"
        response += "• Documents: Marksheet, ID proof, photo\n"
        response += "• Usually June-July me admission start hota hai\n\n"
        
        response += "Detailed info ke liye: https://www.vbspu.ac.in"
        
        return response
    
    def generate_course_response(self, data):
        """Generate course response using scraped data"""
        courses = data.get('courses', {})
        
        response = "VBSPU me ye courses available hain:\n\n"
        
        if courses.get('undergraduate_programs'):
            response += "🔹 **UG Programs**:\n"
            for course in courses['undergraduate_programs']:
                response += f"• {course}\n"
        
        response += "\n"
        
        if courses.get('postgraduate_programs'):
            response += "🔹 **PG Programs**:\n"
            for course in courses['postgraduate_programs']:
                response += f"• {course}\n"
        
        if courses.get('departments'):
            response += f"\n🔹 **Total Departments**: {len(courses['departments'])}\n"
        
        response += "\nFull list aur details ke liye official website check karein."
        
        return response
    
    def generate_fee_response(self, data):
        """Generate fee response using scraped data"""
        fees = data.get('fees', {})
        query = data.get('query', '').lower()
        
        # Check for specific course queries
        course_mapping = {
            'ba': 'b.a', 'b.a': 'b.a', 'bachelor of arts': 'b.a',
            'bsc': 'b.sc', 'b.sc': 'b.sc', 'bachelor of science': 'b.sc',
            'bcom': 'b.com', 'b.com': 'b.com', 'bachelor of commerce': 'b.com',
            'bca': 'bca', 'b.c.a': 'bca',
            'bba': 'bba', 'b.b.a': 'bba',
            'btech': 'b.tech', 'b.tech': 'b.tech',
            'ma': 'm.a', 'm.a': 'm.a', 'master of arts': 'm.a',
            'msc': 'm.sc', 'm.sc': 'm.sc', 'master of science': 'm.sc',
            'mcom': 'm.com', 'm.com': 'm.com', 'master of commerce': 'm.com',
            'mca': 'mca', 'm.c.a': 'mca',
            'mba': 'mba', 'm.b.a': 'mba',
            'mtech': 'm.tech', 'm.tech': 'm.tech'
        }
        
        # Check if user is asking about specific course
        specific_course = None
        for user_term, course_key in course_mapping.items():
            if user_term in query:
                specific_course = course_key
                break
        
        response = "VBSPU fee structure:\n\n"
        
        # If specific course found, show course-specific fee
        if specific_course:
            response += f"🎓 **{specific_course.upper()} Fee Information**:\n\n"
            found_specific = False  # Initialize here
            
            # Check for specific course fees
            if fees.get('course_fees') and specific_course in fees['course_fees']:
                course_fee = fees['course_fees'][specific_course]
                response += f"🎓 **{course_fee.get('name', specific_course.upper())} Fee Information**:\n\n"
                response += f"📊 **Course Type**: {course_fee.get('type', 'N/A')}\n"
                response += f"💰 **Fee Range**: {course_fee.get('fee_range', 'N/A')}\n"
                response += f"⏰ **Duration**: {course_fee.get('duration', 'N/A')}\n"
                
                # Show detailed info if available
                if course_fee.get('detailed_info'):
                    details = course_fee['detailed_info']
                    response += f"\n💵 **Detailed Fee Breakdown**:\n"
                    if details.get('first_year'):
                        response += f"• **1st Year**: {details['first_year']}\n"
                    if details.get('second_year'):
                        response += f"• **2nd Year**: {details['second_year']}\n"
                    if details.get('total_fee'):
                        response += f"• **Total Course Fee**: {details['total_fee']}\n"
                
                found_specific = True
            
            # If no specific data found, provide general info
            if not found_specific:
                if specific_course in ['b.a', 'b.sc', 'b.com', 'bca', 'bba']:
                    response += f"• **UG Course**: {specific_course.upper()}\n"
                    response += f"• **General Fee Range**: {fees.get('undergraduate', {}).get('general', '₹10,000 - ₹50,000 per year')}\n"
                elif specific_course in ['m.a', 'm.sc', 'm.com', 'mca', 'mba']:
                    response += f"• **PG Course**: {specific_course.upper()}\n"
                    response += f"• **General Fee Range**: {fees.get('postgraduate', {}).get('general', '₹15,000 - ₹60,000 per year')}\n"
        
        # Show general fee structure
        response += "🔹 **General Fee Structure**:\n"
        
        if fees.get('undergraduate'):
            ug = fees['undergraduate']
            response += f"• **UG Fees**: {ug.get('general', 'N/A')}\n"
            if ug.get('professional'):
                response += f"• **Professional UG**: {ug['professional']}\n"
        
        if fees.get('postgraduate'):
            pg = fees['postgraduate']
            response += f"• **PG Fees**: {pg.get('general', 'N/A')}\n"
            if pg.get('professional'):
                response += f"• **Professional PG**: {pg['professional']}\n"
        
        # Show available PDF documents
        if fees.get('detailed_fee_structure'):
            response += "\n🔹 **Available Fee Documents**:\n"
            for pdf_name in fees['detailed_fee_structure'].keys():
                response += f"📄 {pdf_name}\n"
        
        response += "\n💰 **For complete fee details**: https://www.vbspu.ac.in/en/article/online-fee20"
        response += "\n📞 **Contact university office for exact amounts**"
        
        return response
    
    def generate_exam_response(self, data):
        """Generate exam response using scraped data"""
        exams = data.get('examinations', {})
        
        response = "VBSPU exam related information:\n\n"
        
        if exams.get('exam_schedule'):
            response += "🔹 **Exam Schedule**:\n"
            for item in exams['exam_schedule'][:3]:
                response += f"• {item.get('title', 'N/A')}\n"
        
        if exams.get('results'):
            response += "\n🔹 **Results**:\n"
            for item in exams['results'][:2]:
                response += f"• {item.get('title', 'N/A')}\n"
        
        if exams.get('admit_cards'):
            response += "\n🔹 **Admit Cards**:\n"
            for item in exams['admit_cards'][:2]:
                response += f"• {item.get('title', 'N/A')}\n"
        
        response += "\nSpecific dates aur links ke liye: https://www.vbspu.ac.in"
        
        return response
    
    def generate_facility_response(self, data):
        """Generate facility response"""
        response = """VBSPU campus facilities:

🔹 **Library**: Central library with large collection, online journals
🔹 **Hostels**: Boys and girls separate hostels with WiFi facility
🔹 **Transport**: Bus facility for local students from different routes
🔹 **Sports**: Ground for cricket, football, volleyball, indoor games
🔹 **Computer Labs**: Modern computer labs with internet facility
🔹 **Cafeteria**: Hygienic food facility for students
🔹 **Medical**: Basic medical facility available on campus
🔹 **SWAYAM**: Online courses and MOOCs available

More info ke liye campus visit karein ya website check karein."""
        
        return response
    
    def generate_news_response(self, data):
        """Generate news response using scraped data"""
        news = data.get('news_notices', {})
        
        response = "VBSPU latest updates:\n\n"
        
        if news.get('latest_news'):
            response += "🔹 **Latest News**:\n"
            for item in news['latest_news'][:5]:
                response += f"• {item.get('title', 'N/A')}\n"
        
        response += "\n🔹 **Official Sources**:\n"
        response += "• University website: vbspu.ac.in\n"
        response += "• Notice board on campus\n"
        response += "• Student portal updates\n\n"
        
        response += "Regular updates ke liye website visit karte rahein."
        
        return response
    
    def generate_contact_response(self):
        """Generate contact response"""
        return """VBSPU Contact Information:

🔹 **Address**: 
Veer Bahadur Singh Purvanchal University,
Jaunpur, Uttar Pradesh - 222001

🔹 **Website**: https://www.vbspu.ac.in

🔹 **Phone**: 
• +91-5452-252285 (Office)
• +91-5452-252286 (Registrar)

🔹 **Email**: 
• registrar@vbspu.ac.in
• info@vbspu.ac.in

🔹 **Social Media**:
• Facebook: /VBSPUOfficial
• Twitter: @VBSPU_Jaunpur

Working hours: 10:00 AM - 5:00 PM (Monday to Saturday)"""

# Initialize bot
bot = UserVBSPUBot()

@user_bp.route('/')
def index():
    """User chat interface"""
    return render_template('index.html')

@user_bp.route('/chat', methods=['POST'])
def chat():
    """Handle user chat messages"""
    try:
        data = request.get_json()
        user_message = data.get('message', '')
        
        if not user_message:
            return jsonify({'error': 'Message is required'}), 400
        
        # Get or create session ID
        session_id = session.get('session_id')
        if not session_id:
            session_id = str(uuid.uuid4())
            session['session_id'] = session_id
        
        # Generate bot response
        response = bot.generate_response(user_message, session_id)
        
        # Save chat to database (optional - for anonymous users, we can use session_id)
        try:
            if response and response.strip():
                db.save_chat_message(None, session_id, user_message, response)
        except Exception as e:
            logger.warning(f"Failed to save chat message: {e}")
        
        return jsonify({
            'response': response,
            'timestamp': datetime.now().strftime('%H:%M:%S')
        })
        
    except Exception as e:
        logger.error(f"Chat error: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@user_bp.route('/api/data/<category>')
def get_category_data(category):
    """Get scraped data by category (for user interface)"""
    try:
        data = db.get_scraped_data(category)
        if data:
            return jsonify({
                'success': True,
                'data': data
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Category not found'
            }), 404
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@user_bp.route('/api/quick-info')
def get_quick_info():
    """Get quick information for user interface"""
    try:
        scraped_data = db.get_scraped_data()
        
        quick_info = {
            'admissions': {
                'status': 'Active' if scraped_data and 'admissions' in scraped_data else 'Offline',
                'last_updated': scraped_data.get('admissions', {}).get('last_updated', 'Unknown')
            },
            'courses': {
                'total_ug': len(scraped_data.get('courses', {}).get('undergraduate_programs', [])),
                'total_pg': len(scraped_data.get('courses', {}).get('postgraduate_programs', []))
            },
            'exams': {
                'status': 'Active' if scraped_data and 'examinations' in scraped_data else 'Offline',
                'last_updated': scraped_data.get('examinations', {}).get('last_updated', 'Unknown')
            },
            'news': {
                'latest_count': len(scraped_data.get('news_notices', {}).get('latest_news', [])),
                'last_updated': scraped_data.get('news_notices', {}).get('last_updated', 'Unknown')
            }
        }
        
        return jsonify({
            'success': True,
            'data': quick_info
        })
        
    except Exception as e:
        logger.error(f"Quick info API error: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to get quick info'
        }), 500
