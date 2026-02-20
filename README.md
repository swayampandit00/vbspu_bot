# VBSPU AI Assistant

This project implements an AI University Assistant for **Veer Bahadur Singh Purvanchal University (VBSPU)**.

## Goal
To help students, parents, and staff with accurate information related to the university, using a respectful and professional Hinglish persona.

## Features
- Answers queries about Admissions, Courses, Fees, Exams, etc.
- Responds in Hinglish (Hindi-English mix).
- Directs users to official sources when necessary.
- Web-based chat interface with modern UI.
- Real-time response system.

## Tech Stack
- **Backend**: Python Flask
- **Frontend**: HTML, CSS, JavaScript
- **UI**: Modern responsive design with animations

## Installation & Setup

### Prerequisites
- Python 3.7 or higher
- pip package manager

### Steps

1. **Clone or download the project**
   ```bash
   # If using git
   git clone <repository-url>
   cd uni_bot
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application**
   ```bash
   python app.py
   ```

4. **Access the bot**
   Open your web browser and go to:
   ```
   http://localhost:5000
   ```

## Usage

1. Open the web interface in your browser
2. Type your question in the input box
3. Press Enter or click "भेजें" to send
4. Get instant responses in Hinglish

### Quick Actions
The bot provides quick action buttons for common queries:
- 📚 Admission Process
- 📖 Courses  
- 💰 Fees
- 📅 Exam Dates

## Bot Capabilities

The VBSPU Assistant can help with:

🔹 **Admissions** — processes, eligibility, and timelines (Samarth portal)
🔹 **Courses & Departments** — UG, PG, and research programs  
🔹 **Fees & Scholarships** — fee structure and scholarship information
🔹 **Exam Dates & Results** — examination schedule, form details, admit cards
🔹 **Facilities** — library, hostels, transport, SWAYAM initiatives
🔹 **News and Notices** — university announcements, updates
🔹 **Placements & Events** — placement fairs and programs

## Important Rules

✔ For specific official data (admit cards, detailed schedules), bot directs to official website
✔ Off-topic queries get: "Main sirf VBSPU se related queries me hi madad kar sakta hoon."
✔ Illegal document requests are politely refused

## Project Structure
```
uni_bot/
├── app.py              # Main Flask application
├── requirements.txt    # Python dependencies
├── system_prompt.md   # Bot system prompt
├── templates/
│   └── index.html     # Web interface
└── README.md          # This file
```

## Configuration

The bot uses the `system_prompt.md` file for its behavior guidelines. You can modify this file to update the bot's responses and rules.

## Development

To modify the bot's responses:
1. Edit the `VBSPUBot.generate_response()` method in `app.py`
2. Update the system prompt in `system_prompt.md`
3. Restart the application

## Official Resources

- **VBSPU Website**: https://www.vbspu.ac.in
- **Samarth Portal**: For admissions (mentioned in bot responses)

## Support

For issues related to:
- **Bot functionality**: Check the code and logs
- **University information**: Visit the official VBSPU website
- **Technical issues**: Verify Python and Flask installation
