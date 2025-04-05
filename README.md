# GitHub Profile Analyzer

A Python web application that analyzes public GitHub profiles and provides insights about user activity, repositories, and programming languages.

## Features

- Analyze any public GitHub profile using their GitHub URL
- View basic profile information (followers, following, repositories)
- See total star count across all repositories
- Discover most used programming languages
- Track account creation and last activity dates

## Prerequisites

- Python 3.8 or higher
- GitHub Personal Access Token (for API access)

## Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd github-profile-analyzer
```

2. Create a virtual environment and activate it:
```bash
python -m venv venv
# On Windows
venv\Scripts\activate
# On Unix or MacOS
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file:
- Copy `.env.example` to `.env`
- Add your GitHub Personal Access Token:
```
GITHUB_TOKEN=your_github_token_here
```

To get a GitHub Personal Access Token:
1. Go to GitHub Settings
2. Developer Settings
3. Personal Access Tokens
4. Generate new token (classic)
5. Select `read:user` and `repo` scopes

## Usage

1. Start the application:
```bash
python github_analyzer.py
```

2. Open your web browser and navigate to:
```
http://localhost:5000
```

3. Enter a GitHub profile URL and click "Analyze Profile"

## Error Handling

The application handles various error cases:
- Invalid GitHub URLs
- Non-existent profiles
- API rate limiting
- Authentication issues

## Contributing

Feel free to submit issues and enhancement requests! 