from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
from admin.admin_routes import admin_bp
from user.user_routes import user_bp
from database import DatabaseManager
from scraper import VBSPUScraper
import os
import json
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = 'vbspu_bot_secret_key_2024'

# Initialize database
db = DatabaseManager()

# Initialize scraper
scraper = VBSPUScraper()

# Register blueprints
app.register_blueprint(admin_bp, url_prefix='/admin')
app.register_blueprint(user_bp, url_prefix='/user')

# Load system prompt
def load_system_prompt():
    try:
        with open('system_prompt.md', 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return "You are a helpful university assistant."

SYSTEM_PROMPT = load_system_prompt()

class EnhancedVBSPUBot:
    def __init__(self):
        self.system_prompt = SYSTEM_PROMPT
        self.db = db
        self.scraper = scraper
        
    def get_relevant_data(self, query):
        """Get relevant data from scraped information"""
        # Get all scraped data from database
        all_data = self.db.get_scraped_data()
        if not all_data:
            return {}
        
        query = query.lower()
        relevant_info = {}
        
        # Check what category the query belongs to
        if any(word in query for word in ['admission', 'admit', 'apply', 'entrance']):
            relevant_info = {'fees': all_data.get('fees', {})}
        elif any(word in query for word in ['course', 'department', 'program', 'study']):
            relevant_info = {'courses': all_data.get('courses', {})}
        elif any(word in query for word in ['exam', 'result', 'date', 'schedule']):
            relevant_info = {'examinations': all_data.get('examinations', {})}
        elif any(word in query for word in ['fee', 'fees', 'scholarship', 'cost']):
            relevant_info = {'fees': all_data.get('fees', {})}
        elif any(word in query for word in ['news', 'notice', 'announcement', 'update']):
            relevant_info = {'news_notices': all_data.get('news_notices', {})}
        else:
            # Return general info with fees for default
            relevant_info = {
                'fees': all_data.get('fees', {}),
                'courses': all_data.get('courses', {})
            }
        
        # Add course detection context
        relevant_info['query'] = query
        return relevant_info
    
    def generate_response(self, user_message, session_id=None):
        """Generate enhanced response using scraped data"""
        user_message = user_message.strip().lower()
        
        # Get relevant scraped data
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
        
        # Handle specific official data requests
        official_data_keywords = ['admit card', 'specific date', 'exact fee', 'roll number', 'registration link']
        if any(keyword in user_message for keyword in official_data_keywords):
            return "Official information available on university website / portal. Kripya https://www.vbspu.ac.in par visit karein."
        
        # Enhanced responses using scraped data
        if any(word in user_message for word in ['admission', 'admit', 'entrance', 'apply']):
            return self.generate_admission_response(relevant_data)
        
        elif any(word in user_message for word in ['course', 'department', 'program', 'study']):
            return self.generate_course_response(relevant_data)
        
        elif any(word in user_message for word in ['fee', 'fees', 'scholarship', 'cost']):
            return self.generate_fee_response(relevant_data)
        
        elif any(word in user_message for word in ['exam', 'result', 'date', 'schedule']):
            return self.generate_exam_response(relevant_data)
        
        elif any(word in user_message for word in ['hostel', 'library', 'facility', 'transport']):
            return self.generate_facility_response(relevant_data)
        
        elif any(word in user_message for word in ['news', 'notice', 'announcement', 'update']):
            return self.generate_news_response(relevant_data)
        
        elif any(word in user_message for word in ['contact', 'phone', 'address', 'email']):
            return self.generate_contact_response()
        
        else:
            # Default response
            welcome_msg = self.db.get_setting('welcome_message') or "नमस्ते! मैं VBSPU AI Assistant हूं। क्या जानना चाहते हैं आप?"
            return f"""{welcome_msg}

मैं आपको इन विषयों में मदद कर सकता हूं:

🔹 Admissions aur courses
🔹 Fees aur scholarships  
🔹 Exam dates aur results
🔹 Facilities aur campus info
🔹 News aur notices

आप क्या जानना चाहते हैं?"""
    
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
        
        response += "Detailed info ke liye: https://www.vbspu.acin"
        
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
            
            # Check detailed fee structure for specific course
            if fees.get('detailed_fee_structure'):
                for pdf_name, fee_details in fees['detailed_fee_structure'].items():
                    if fee_details.get('course_fees') and specific_course in fee_details['course_fees']:
                        course_fee = fee_details['course_fees'][specific_course]
                        response += f"📄 **From {pdf_name}**:\n"
                        response += f"• Course: {course_fee.get('name', specific_course.upper())}\n"
                        response += f"• Fee Details: {course_fee.get('fee_info', 'N/A')}\n"
                        response += f"• Amount: {course_fee.get('amount', 'N/A')}\n\n"
                        found_specific = True
                        break
                
                if not found_specific:
                    # Look in general course lists
                    for pdf_name, fee_details in fees['detailed_fee_structure'].items():
                        courses = fee_details.get('undergraduate_courses', [])
                        if any(specific_course.replace('.', '').upper() in course.upper() for course in courses):
                            response += f"📄 **From {pdf_name}**:\n"
                            response += "• Course fee information available:\n"
                            for course in courses[:3]:
                                if specific_course.replace('.', '').upper() in course.upper():
                                    response += f"  - {course}\n"
                            response += "\n"
                            found_specific = True
                            break
            
            # If no specific data found, provide general info
            if not found_specific and specific_course in ['b.a', 'b.sc', 'b.com', 'bca', 'bba']:
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
        
        # Detailed fee structure from PDF
        if fees.get('detailed_fee_structure'):
            response += "\n🔹 **Detailed Fee Information Available**:\n"
            for pdf_name, fee_details in fees['detailed_fee_structure'].items():
                response += f"📄 {pdf_name}\n"
                
                if fee_details.get('course_fees'):
                    response += "  • Course-wise fees available\n"
                
                if fee_details.get('other_fees'):
                    response += "  • Other fees: " + ", ".join(list(fee_details['other_fees'].keys())[:3]) + "\n"
        
        # Fee tables if available
        if fees.get('fee_tables'):
            response += "\n🔹 **Official Fee Tables**: Available on university website\n"
        
        # Scholarships
        if fees.get('scholarships'):
            response += "\n🔹 **Scholarships**:\n"
            for scholarship in fees['scholarships'][:4]:
                response += f"• {scholarship}\n"
        
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

# Initialize enhanced bot
bot = EnhancedVBSPUBot()

@app.route('/')
def index():
    return redirect(url_for('user.index'))

@app.route('/health')
def health():
    return jsonify({
        'status': 'healthy', 
        'timestamp': datetime.now().isoformat(),
        'bot_status': 'active'
    })

@app.route('/api/scrape', methods=['POST'])
def manual_scrape():
    """Manual scraping endpoint"""
    try:
        data = scraper.scrape_all()
        scraper.save_to_database(data)
        
        # Save to database as well
        for category, category_data in data.items():
            db.save_scraped_data(category, category_data)
        
        return jsonify({
            'success': True,
            'message': 'Scraping completed successfully',
            'data': data
        })
    except Exception as e:
        logger.error(f"Scraping error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/data/<category>')
def get_category_data(category):
    """Get scraped data by category"""
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

if __name__ == '__main__':
    # Initialize database and scrape initial data
    logger.info("Initializing VBSPU Bot...")
    
    # Try to load existing data, if not available, scrape
    existing_data = db.get_scraped_data()
    if not existing_data:
        logger.info("No existing data found, starting initial scrape...")
        try:
            data = scraper.scrape_all()
            scraper.save_to_database(data)
            
            # Save to database
            for category, category_data in data.items():
                db.save_scraped_data(category, category_data)
            
            logger.info("Initial scraping completed")
        except Exception as e:
            logger.error(f"Initial scraping failed: {e}")
            logger.info("Bot will run with default responses")
    
    logger.info("VBSPU Bot starting on http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)
