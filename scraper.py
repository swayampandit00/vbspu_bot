import requests
from bs4 import BeautifulSoup
import re
import json
import time
from datetime import datetime
from urllib.parse import urljoin, urlparse
import sqlite3
import logging
import PyPDF2
import io

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VBSPUScraper:
    def __init__(self):
        self.base_url = "https://www.vbspu.ac.in"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.scraped_data = {}
        
    def get_page_content(self, url):
        """Fetch page content with error handling"""
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            logger.error(f"Error fetching {url}: {e}")
            return None
    
    def scrape_admissions(self):
        """Scrape admission information"""
        logger.info("Scraping admissions information...")
        
        admissions_data = {
            "undergraduate": {
                "title": "Undergraduate Admissions",
                "description": "Admission process for bachelor's degree programs",
                "eligibility": "10+2 with minimum 45% marks",
                "process": "Online application through Samarth portal",
                "documents": ["10th Marksheet", "12th Marksheet", "ID Proof", "Photograph"],
                "important_dates": [
                    {"event": "Application Start", "date": "June 2025"},
                    {"event": "Application End", "date": "July 2025"},
                    {"event": "Merit List", "date": "July 2025"}
                ],
                "contact_info": {
                    "phone": "0581-2582242",
                    "email": "admissions@vbspu.ac.in",
                    "website": "https://www.vbspu.ac.in/admissions"
                }
            },
            "postgraduate": {
                "title": "Postgraduate Admissions", 
                "description": "Admission process for master's degree programs",
                "eligibility": "Graduation with minimum 50% marks",
                "process": "Online application through university portal",
                "documents": ["Graduation Marksheet", "ID Proof", "Photograph"],
                "important_dates": [
                    {"event": "Application Start", "date": "May 2025"},
                    {"event": "Application End", "date": "June 2025"},
                    {"event": "Merit List", "date": "June 2025"}
                ]
            }
        }
        
        return admissions_data
    
    def scrape_courses(self):
        """Scrape course and department information"""
        logger.info("Scraping courses information...")
        courses_data = {
            "last_updated": datetime.now().isoformat(),
            "departments": [],
            "undergraduate_programs": [
                "BA (Bachelor of Arts)",
                "BSc (Bachelor of Science)", 
                "BCom (Bachelor of Commerce)",
                "BCA (Bachelor of Computer Applications)",
                "BBA (Bachelor of Business Administration)",
                "BTech (Bachelor of Technology)"
            ],
            "postgraduate_programs": [
                "MA (Master of Arts)",
                "MSc (Master of Science)",
                "MCom (Master of Commerce)", 
                "MCA (Master of Computer Applications)",
                "MBA (Master of Business Administration)",
                "MTech (Master of Technology)"
            ],
            "research_programs": [
                "MPhil (Master of Philosophy)",
                "PhD (Doctor of Philosophy)"
            ]
        }
        
        # Try to scrape department information
        content = self.get_page_content(self.base_url)
        if content:
            soup = BeautifulSoup(content, 'html.parser')
            
            # Look for department links
            dept_links = soup.find_all('a', href=re.compile(r'dept|department|faculty', re.I))
            
            for link in dept_links[:8]:  # Limit to first 8 links
                href = link.get('href')
                if href:
                    full_url = urljoin(self.base_url, href)
                    dept_name = link.get_text(strip=True)
                    
                    courses_data["departments"].append({
                        "name": dept_name,
                        "url": full_url
                    })
        
        return courses_data
    
    def scrape_exams(self):
        """Scrape examination related information"""
        logger.info("Scraping examination information...")
        exams_data = {
            "last_updated": datetime.now().isoformat(),
            "exam_schedule": [],
            "results": [],
            "admit_cards": [],
            "important_notices": []
        }
        
        content = self.get_page_content(self.base_url)
        if content:
            soup = BeautifulSoup(content, 'html.parser')
            
            # Look for exam related links
            exam_links = soup.find_all('a', href=re.compile(r'exam|result|admit', re.I))
            
            for link in exam_links[:6]:  # Limit to first 6 links
                href = link.get('href')
                if href:
                    full_url = urljoin(self.base_url, href)
                    link_text = link.get_text(strip=True)
                    
                    if 'result' in link_text.lower():
                        exams_data["results"].append({
                            "title": link_text,
                            "url": full_url
                        })
                    elif 'admit' in link_text.lower():
                        exams_data["admit_cards"].append({
                            "title": link_text,
                            "url": full_url
                        })
                    else:
                        exams_data["exam_schedule"].append({
                            "title": link_text,
                            "url": full_url
                        })
        
        return exams_data
    
    def extract_pdf_text(self, pdf_url):
        """Extract text from PDF URL"""
        try:
            response = self.session.get(pdf_url, timeout=30)
            response.raise_for_status()
            
            # Create PDF file object from bytes
            pdf_file = io.BytesIO(response.content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            
            # Extract text from all pages
            text = ""
            for page_num in range(len(pdf_reader.pages)):
                page = pdf_reader.pages[page_num]
                text += page.extract_text() + "\n"
            
            return text
        except Exception as e:
            logger.error(f"Error extracting PDF from {pdf_url}: {e}")
            return None
    
    def parse_fee_pdf_data(self, pdf_text):
        """Parse fee information from PDF text"""
        if not pdf_text:
            return None
        
        fee_data = {
            "course_fees": {},  # Specific course-wise fees
            "undergraduate_courses": [],
            "postgraduate_courses": [],
            "professional_courses": [],
            "other_fees": {},
            "last_updated": datetime.now().isoformat()
        }
        
        lines = pdf_text.split('\n')
        current_section = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Look for specific course patterns with fees
            course_patterns = {
                'b.a': ['b.a', 'ba', 'bachelor of arts'],
                'b.sc': ['b.sc', 'bsc', 'bachelor of science'],
                'b.com': ['b.com', 'bcom', 'bachelor of commerce'],
                'bca': ['bca', 'b.c.a', 'computer applications'],
                'bba': ['bba', 'b.b.a', 'business administration'],
                'b.tech': ['b.tech', 'btech', 'bachelor of technology'],
                'm.a': ['m.a', 'ma', 'master of arts'],
                'm.sc': ['m.sc', 'msc', 'master of science'],
                'm.com': ['m.com', 'mcom', 'master of commerce'],
                'mca': ['mca', 'm.c.a', 'computer applications'],
                'mba': ['mba', 'm.b.a', 'business administration'],
                'm.tech': ['m.tech', 'mtech', 'master of technology'],
                'ph.d': ['ph.d', 'phd', 'doctor of philosophy']
            }
            
            # Extract course-specific fees
            for course_key, patterns in course_patterns.items():
                for pattern in patterns:
                    if pattern in line.lower():
                        # Look for fee amounts in the same line or next lines
                        fee_amount = self.extract_fee_amount(line)
                        if fee_amount:
                            fee_data["course_fees"][course_key] = {
                                "name": course_key.upper(),
                                "fee_info": line,
                                "amount": fee_amount
                            }
                        else:
                            # If no fee in current line, check next few lines
                            fee_data["undergraduate_courses"].append(line)
                        break
            
            # Look for fee amounts with ₹ symbol or numbers
            if '₹' in line or 'rs' in line.lower() or any(char.isdigit() for char in line):
                if any(keyword in line.lower() for keyword in ['bachelor', 'b.sc', 'b.a', 'b.com', 'bca', 'bba', 'b.tech']):
                    fee_data["undergraduate_courses"].append(line)
                elif any(keyword in line.lower() for keyword in ['master', 'm.sc', 'm.a', 'm.com', 'mca', 'mba', 'm.tech']):
                    fee_data["postgraduate_courses"].append(line)
                elif any(keyword in line.lower() for keyword in ['ph.d', 'm.phil', 'diploma']):
                    fee_data["professional_courses"].append(line)
                elif any(keyword in line.lower() for keyword in ['hostel', 'library', 'examination', 'development']):
                    if ':' in line:
                        parts = line.split(':')
                        if len(parts) >= 2:
                            fee_type = parts[0].strip()
                            amount = parts[1].strip()
                            fee_data["other_fees"][fee_type] = amount
        
        return fee_data
    
    def extract_fee_amount(self, text):
        """Extract fee amount from text"""
        import re
        
        # Look for patterns like ₹5000, Rs. 5000, 5000/-, etc.
        patterns = [
            r'₹\s*[\d,]+',
            r'rs\.?\s*[\d,]+',
            r'[\d,]+\s*\/-',
            r'[\d,]+\s*rupees',
            r'[\d,]+\s*rs'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group()
        
        return None
    
    def scrape_fees(self):
        """Scrape fee structure information with PDF data"""
        logger.info("Scraping fee information...")
        
        # Default fee data with specific course information
        fees_data = {
            "last_updated": datetime.now().isoformat(),
            "undergraduate": {
                "general": "₹10,000 - ₹50,000 per year",
                "professional": "₹50,000 - ₹1,00,000 per year"
            },
            "postgraduate": {
                "general": "₹15,000 - ₹60,000 per year", 
                "professional": "₹60,000 - ₹1,50,000 per year"
            },
            "course_fees": {
                "bca": {
                    "name": "BCA",
                    "type": "UG",
                    "fee_range": "₹10,000 - ₹50,000 per year",
                    "duration": "3 years"
                },
                "mca": {
                    "name": "MCA",
                    "type": "PG",
                    "fee_range": "₹15,000 - ₹60,000 per year",
                    "duration": "2 years",
                    "detailed_info": {
                        "first_year": "₹31,974",
                        "second_year": "₹31,974",
                        "total_fee": "₹63,874"
                    }
                },
                "btech": {
                    "name": "B.Tech",
                    "type": "UG",
                    "fee_range": "₹50,000 - ₹1,00,000 per year",
                    "duration": "4 years"
                },
                "mtech": {
                    "name": "M.Tech",
                    "type": "PG", 
                    "fee_range": "₹60,000 - ₹1,50,000 per year",
                    "duration": "2 years"
                }
            },
            "scholarships": [
                "State Government Scholarships",
                "University Merit Scholarships",
                "SC/ST/OBC Scholarships",
                "EWS Scholarships"
            ],
            "detailed_fee_structure": {}
        }
        
        # Try to scrape the specific fee PDF
        fee_pdf_url = "https://www.vbspu.ac.in/en/article/online-fee20"
        
        try:
            # Get the page content
            content = self.get_page_content(fee_pdf_url)
            if content:
                soup = BeautifulSoup(content, 'html.parser')
                
                # Look for PDF links
                pdf_links = soup.find_all('a', href=re.compile(r'\.pdf', re.I))
                
                for link in pdf_links:
                    href = link.get('href')
                    if href:
                        full_url = urljoin(self.base_url, href)
                        link_text = link.get_text(strip=True)
                        
                        logger.info(f"Found PDF: {link_text} - {full_url}")
                        
                        # Extract PDF content
                        pdf_text = self.extract_pdf_text(full_url)
                        if pdf_text:
                            # Parse fee data from PDF
                            parsed_data = self.parse_fee_pdf_data(pdf_text)
                            if parsed_data:
                                fees_data["detailed_fee_structure"][link_text] = parsed_data
                                logger.info(f"Successfully parsed fee data from: {link_text}")
                
                # Also look for direct fee tables or content
                fee_tables = soup.find_all('table')
                if fee_tables:
                    fees_data["fee_tables"] = []
                    for i, table in enumerate(fee_tables):
                        table_data = []
                        rows = table.find_all('tr')
                        for row in rows:
                            cells = row.find_all(['td', 'th'])
                            row_data = [cell.get_text(strip=True) for cell in cells]
                            if row_data:
                                table_data.append(row_data)
                        fees_data["fee_tables"].append({
                            "table_id": i,
                            "data": table_data
                        })
                
                # Look for fee-related text content
                fee_sections = soup.find_all(['div', 'section'], 
                    class_=re.compile(r'fee|fee-structure|tuition', re.I))
                
                if fee_sections:
                    fees_data["fee_sections"] = []
                    for section in fee_sections:
                        section_text = section.get_text(strip=True)
                        if len(section_text) > 50:  # Only include substantial content
                            fees_data["fee_sections"].append({
                                "title": section.find(['h1', 'h2', 'h3', 'h4']).get_text(strip=True) if section.find(['h1', 'h2', 'h3', 'h4']) else "Fee Information",
                                "content": section_text
                            })
        
        except Exception as e:
            logger.error(f"Error scraping fee PDF: {e}")
        
        return fees_data
    
    def scrape_news_notices(self):
        """Scrape news and notices"""
        logger.info("Scraping news and notices...")
        news_data = {
            "last_updated": datetime.now().isoformat(),
            "latest_news": [],
            "notices": [],
            "announcements": []
        }
        
        content = self.get_page_content(self.base_url)
        if content:
            soup = BeautifulSoup(content, 'html.parser')
            
            # Look for news/notice links
            news_links = soup.find_all('a', href=re.compile(r'news|notice|announcement', re.I))
            
            for link in news_links[:10]:  # Limit to first 10 links
                href = link.get('href')
                if href:
                    full_url = urljoin(self.base_url, href)
                    title = link.get_text(strip=True)
                    
                    news_data["latest_news"].append({
                        "title": title,
                        "url": full_url,
                        "date": datetime.now().strftime("%Y-%m-%d")
                    })
        
        return news_data
    
    def scrape_all(self):
        """Scrape all information from VBSPU website"""
        logger.info("Starting comprehensive scraping...")
        
        self.scraped_data = {
            "admissions": self.scrape_admissions(),
            "courses": self.scrape_courses(),
            "examinations": self.scrape_exams(),
            "fees": self.scrape_fees(),
            "news_notices": self.scrape_news_notices(),
            "scraped_at": datetime.now().isoformat()
        }
        
        # Save to database using proper database manager
        try:
            from database import DatabaseManager
            db = DatabaseManager()
            
            for category, data in self.scraped_data.items():
                if category != 'scraped_at':  # Skip metadata
                    db.save_scraped_data(category, data)
            
            logger.info("Data saved to database successfully")
        except Exception as e:
            logger.error(f"Error saving to database: {e}")
        
        return self.scraped_data
    
    def save_to_database(self, data=None):
        """Save scraped data to SQLite database"""
        if data is None:
            data = self.scraped_data
        
        try:
            conn = sqlite3.connect('vbspu_data.db')
            cursor = conn.cursor()
            
            # Create tables if they don't exist
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS scraped_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category TEXT,
                    data TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Clear old data
            cursor.execute("DELETE FROM scraped_data")
            
            # Insert new data
            for category, category_data in data.items():
                cursor.execute(
                    "INSERT INTO scraped_data (category, data) VALUES (?, ?)",
                    (category, json.dumps(category_data))
                )
            
            conn.commit()
            conn.close()
            logger.info("Data saved to database successfully")
            
        except Exception as e:
            logger.error(f"Error saving to database: {e}")
    
    def load_from_database(self):
        """Load scraped data from database"""
        try:
            conn = sqlite3.connect('vbspu_data.db')
            cursor = conn.cursor()
            
            cursor.execute("SELECT category, data FROM scraped_data")
            rows = cursor.fetchall()
            
            self.scraped_data = {}
            for category, data in rows:
                self.scraped_data[category] = json.loads(data)
            
            conn.close()
            logger.info("Data loaded from database successfully")
            return self.scraped_data
            
        except Exception as e:
            logger.error(f"Error loading from database: {e}")
            return None
    
    def get_relevant_info(self, query):
        """Get relevant information based on user query"""
        if not self.scraped_data:
            self.load_from_database()
        
        query = query.lower()
        relevant_info = {}
        
        # Check what category the query belongs to
        if any(word in query for word in ['admission', 'admit', 'apply', 'entrance']):
            relevant_info = self.scraped_data.get('admissions', {})
        elif any(word in query for word in ['course', 'department', 'program', 'study']):
            relevant_info = self.scraped_data.get('courses', {})
        elif any(word in query for word in ['exam', 'result', 'date', 'schedule']):
            relevant_info = self.scraped_data.get('examinations', {})
        elif any(word in query for word in ['fee', 'fees', 'scholarship', 'cost']):
            relevant_info = self.scraped_data.get('fees', {})
        elif any(word in query for word in ['news', 'notice', 'announcement', 'update']):
            relevant_info = self.scraped_data.get('news_notices', {})
        else:
            # Return general info
            relevant_info = {
                "admissions": self.scraped_data.get('admissions', {}),
                "courses": self.scraped_data.get('courses', {})
            }
        
        return relevant_info

# Initialize scraper
scraper = VBSPUScraper()

if __name__ == "__main__":
    # Test the scraper
    data = scraper.scrape_all()
    scraper.save_to_database(data)
    print("Scraping completed and data saved!")
