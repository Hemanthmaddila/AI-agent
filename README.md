# AI Job Application Agent

An intelligent automation system that helps streamline the job application process using AI-powered tools.

## Features

- **Job Discovery**: Automatically find relevant job postings based on your profile
- **Resume Optimization**: Tailor your resume for specific job requirements using AI
- **Application Automation**: Automate form filling and application submission
- **Human-in-the-Loop**: Review and approve applications before submission
- **Application Tracking**: Monitor the status of your job applications
- **AI Integration**: Powered by Google Gemini for intelligent decision making

## Project Structure

```
ai_job_application_agent/
├── app/                        # Main application code
│   ├── agent_orchestrator.py   # Main coordination logic
│   ├── discovery/              # Job discovery module
│   ├── resume_management/      # Resume optimization
│   ├── application_automation/ # Form filling automation
│   ├── hitl/                   # Human-in-the-loop interface
│   ├── tracking/               # Application tracking
│   ├── services/               # External service integrations
│   └── models/                 # Data models
├── config/                     # Configuration management
├── data/                       # Data storage
│   ├── logs/                   # Application logs
│   ├── user_profiles/          # User profile data
│   └── output_resumes/         # Generated resumes
├── notebooks/                  # Jupyter notebooks for analysis
├── scripts/                    # Utility scripts
├── tests/                      # Test suite
└── main.py                     # CLI entry point
```

## Setup

1. **Clone the repository** (if using Git)
2. **Create a virtual environment**:
   ```bash
   python -m venv venv
   ```
3. **Activate the virtual environment**:
   - Windows: `venv\Scripts\activate`
   - macOS/Linux: `source venv/bin/activate`
4. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
5. **Set up environment variables**:
   - Copy `.env.example` to `.env`
   - Fill in your API keys and configuration

## Configuration

Create a `.env` file with the following variables:

```env
GOOGLE_API_KEY=your_gemini_api_key_here
SERPAPI_KEY=your_serpapi_key_here
DATABASE_URL=sqlite:///data/agent_database.db
CAPSOLVER_API_KEY=your_capsolver_api_key_here
```

## Usage

Run the main CLI application:

```bash
python main.py
```

## Development

### Running Tests

```bash
pytest
```

### Code Structure

- **Modular Design**: Each component is separated into its own module
- **Service Layer**: External integrations are abstracted into service classes
- **Data Models**: Pydantic models for data validation and structure
- **Configuration**: Centralized configuration management

## Contributing

1. Follow the existing code structure
2. Add tests for new functionality
3. Update documentation as needed
4. Ensure all tests pass before submitting

## License

[Add your license information here] 