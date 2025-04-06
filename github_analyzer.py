import os
import re
import logging
from datetime import datetime, timedelta
import pandas as pd
import plotly.express as px
from github import Github
from github.GithubException import GithubException
from dotenv import load_dotenv
from flask import Flask, render_template_string, request, jsonify, g
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from urllib.parse import urlparse
from functools import lru_cache
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Initialize rate limiter
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

# Cache configuration
CACHE_TTL = 3600  # 1 hour cache TTL
cache = {}

# HTML template for the web interface
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>GitHub Profile Analyzer</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/font-awesome@4.7.0/css/font-awesome.min.css" rel="stylesheet">
    <style>
        body { padding: 20px; }
        .container { max-width: 800px; }
        .result-section { margin-top: 20px; }
        .loading { display: none; }
        .error-message { display: none; }
        .chart-container { margin-top: 20px; }
        .profile-stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; }
        .stat-card { background: #f8f9fa; padding: 15px; border-radius: 8px; }
        .language-badge { margin-right: 5px; margin-bottom: 5px; }
    </style>
</head>
<body>
    <div class="container">
        <h1 class="mb-4">GitHub Profile Analyzer</h1>
        <form id="analyzeForm" class="mb-4">
            <div class="mb-3">
                <label for="github_url" class="form-label">GitHub Profile URL</label>
                <input type="text" class="form-control" id="github_url" name="github_url" 
                       placeholder="https://github.com/username" required>
                <div class="form-text">Enter a valid GitHub profile URL</div>
            </div>
            <button type="submit" class="btn btn-primary">
                <i class="fa fa-github"></i> Analyze Profile
            </button>
        </form>
        
        <div id="loading" class="loading alert alert-info">
            <i class="fa fa-spinner fa-spin"></i> Analyzing profile...
        </div>
        
        <div id="error" class="error-message alert alert-danger"></div>
        
        <div id="results" class="result-section"></div>
    </div>
    <script>
        document.getElementById('analyzeForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const url = document.getElementById('github_url').value;
            const resultsDiv = document.getElementById('results');
            const loadingDiv = document.getElementById('loading');
            const errorDiv = document.getElementById('error');
            
            // Reset display
            resultsDiv.innerHTML = '';
            errorDiv.style.display = 'none';
            loadingDiv.style.display = 'block';
            
            try {
                const response = await fetch('/analyze', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({github_url: url})
                });
                
                const data = await response.json();
                
                if (data.error) {
                    errorDiv.textContent = data.error;
                    errorDiv.style.display = 'block';
                } else {
                    resultsDiv.innerHTML = `
                        <div class="card">
                            <div class="card-body">
                                <h2 class="card-title">${data.username}'s Profile Analysis</h2>
                                
                                <div class="profile-stats">
                                    <div class="stat-card">
                                        <h5>Repositories</h5>
                                        <p class="display-6">${data.repo_count}</p>
                                    </div>
                                    <div class="stat-card">
                                        <h5>Followers</h5>
                                        <p class="display-6">${data.followers}</p>
                                    </div>
                                    <div class="stat-card">
                                        <h5>Following</h5>
                                        <p class="display-6">${data.following}</p>
                                    </div>
                                    <div class="stat-card">
                                        <h5>Total Stars</h5>
                                        <p class="display-6">${data.total_stars}</p>
                                    </div>
                                </div>
                                
                                <div class="mt-4">
                                    <h4>Most Used Languages</h4>
                                    <div>
                                        ${data.top_languages.map(lang => 
                                            `<span class="badge bg-primary language-badge">${lang}</span>`
                                        ).join('')}
                                    </div>
                                </div>
                                
                                <div class="mt-4">
                                    <h4>Activity Timeline</h4>
                                    <p><strong>Account Created:</strong> ${data.created_at}</p>
                                    <p><strong>Last Active:</strong> ${data.last_active}</p>
                                </div>
                                
                                <div class="mt-4">
                                    <h4>Repository Statistics</h4>
                                    <p><strong>Average Stars per Repo:</strong> ${data.avg_stars_per_repo.toFixed(2)}</p>
                                    <p><strong>Most Starred Repo:</strong> ${data.most_starred_repo}</p>
                                </div>
                            </div>
                        </div>
                    `;
                }
            } catch (error) {
                errorDiv.textContent = 'An error occurred while analyzing the profile.';
                errorDiv.style.display = 'block';
            } finally {
                loadingDiv.style.display = 'none';
            }
        });
    </script>
</body>
</html>
'''

def validate_github_url(url):
    """Validate and sanitize GitHub URL."""
    if not url:
        raise ValueError("URL cannot be empty")
    
    # Basic URL validation
    if not re.match(r'^https?://(www\.)?github\.com/[a-zA-Z0-9_-]+/?$', url):
        raise ValueError("Invalid GitHub URL format")
    
    return url.strip()

@lru_cache(maxsize=100)
def get_cached_github_data(username):
    """Get cached GitHub data or fetch new data."""
    cache_key = f"github_data_{username}"
    if cache_key in cache and time.time() - cache[cache_key]['timestamp'] < CACHE_TTL:
        return cache[cache_key]['data']
    
    return None

def set_cached_github_data(username, data):
    """Cache GitHub data."""
    cache_key = f"github_data_{username}"
    cache[cache_key] = {
        'data': data,
        'timestamp': time.time()
    }

def extract_username_from_url(github_url):
    """Extract username from GitHub URL."""
    parsed = urlparse(github_url)
    if 'github.com' not in parsed.netloc:
        raise ValueError("Not a valid GitHub URL")
    
    path_parts = parsed.path.strip('/').split('/')
    if not path_parts:
        raise ValueError("No username found in URL")
    
    return path_parts[0]

def analyze_github_profile(github_url):
    """Analyze a GitHub profile and return relevant statistics."""
    try:
        # Validate and sanitize input
        github_url = validate_github_url(github_url)
        username = extract_username_from_url(github_url)
        
        # Check cache first
        cached_data = get_cached_github_data(username)
        if cached_data:
            logger.info(f"Using cached data for {username}")
            return cached_data
        
        # Initialize GitHub client
        g = Github(os.getenv('GITHUB_TOKEN'))
        user = g.get_user(username)
        
        # Collect basic user information
        basic_info = {
            'username': username,
            'repo_count': user.public_repos,
            'followers': user.followers,
            'following': user.following,
            'created_at': user.created_at.strftime('%Y-%m-%d'),
            'last_active': user.updated_at.strftime('%Y-%m-%d'),
        }
        
        # Analyze repositories
        repos = user.get_repos()
        languages = {}
        total_stars = 0
        most_starred_repo = None
        max_stars = 0
        
        for repo in repos:
            total_stars += repo.stargazers_count
            if repo.stargazers_count > max_stars:
                max_stars = repo.stargazers_count
                most_starred_repo = repo.name
            
            repo_langs = repo.get_languages()
            for lang, bytes_count in repo_langs.items():
                languages[lang] = languages.get(lang, 0) + bytes_count
        
        # Calculate average stars per repo
        avg_stars_per_repo = total_stars / basic_info['repo_count'] if basic_info['repo_count'] > 0 else 0
        
        # Get top 5 languages
        top_languages = sorted(languages.items(), key=lambda x: x[1], reverse=True)[:5]
        top_languages = [lang for lang, _ in top_languages]
        
        analysis_results = {
            **basic_info,
            'total_stars': total_stars,
            'top_languages': top_languages,
            'avg_stars_per_repo': avg_stars_per_repo,
            'most_starred_repo': most_starred_repo
        }
        
        # Cache the results
        set_cached_github_data(username, analysis_results)
        
        return analysis_results
        
    except GithubException as e:
        logger.error(f"GitHub API error for {username}: {str(e)}")
        if e.status == 404:
            raise ValueError("GitHub profile not found")
        elif e.status == 403:
            raise ValueError("API rate limit exceeded or authentication required")
        else:
            raise ValueError(f"GitHub API error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error analyzing {username}: {str(e)}")
        raise ValueError(f"An unexpected error occurred: {str(e)}")

@app.route('/')
def home():
    """Render the home page."""
    return render_template_string(HTML_TEMPLATE)

@app.route('/analyze', methods=['POST'])
@limiter.limit("10 per minute")
def analyze():
    """API endpoint to analyze a GitHub profile."""
    try:
        github_url = request.json.get('github_url')
        if not github_url:
            return jsonify({'error': 'GitHub URL is required'}), 400
        
        analysis_results = analyze_github_profile(github_url)
        return jsonify(analysis_results)
    
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Unexpected error in analyze endpoint: {str(e)}")
        return jsonify({'error': 'An unexpected error occurred'}), 500

if __name__ == '__main__':
    app.run(debug=True) 