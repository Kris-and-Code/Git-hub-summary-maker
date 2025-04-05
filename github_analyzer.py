import os
from datetime import datetime
import pandas as pd
import plotly.express as px
from github import Github
from github.GithubException import GithubException
from dotenv import load_dotenv
from flask import Flask, render_template_string, request, jsonify
from urllib.parse import urlparse

# Load environment variables
load_dotenv()

app = Flask(__name__)

# HTML template for the web interface
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>GitHub Profile Analyzer</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { padding: 20px; }
        .container { max-width: 800px; }
        .result-section { margin-top: 20px; }
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
            </div>
            <button type="submit" class="btn btn-primary">Analyze Profile</button>
        </form>
        <div id="results" class="result-section"></div>
    </div>
    <script>
        document.getElementById('analyzeForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const url = document.getElementById('github_url').value;
            const resultsDiv = document.getElementById('results');
            resultsDiv.innerHTML = '<div class="alert alert-info">Analyzing profile...</div>';
            
            try {
                const response = await fetch('/analyze', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({github_url: url})
                });
                const data = await response.json();
                
                if (data.error) {
                    resultsDiv.innerHTML = `<div class="alert alert-danger">${data.error}</div>`;
                } else {
                    resultsDiv.innerHTML = `
                        <div class="card">
                            <div class="card-body">
                                <h2 class="card-title">Profile Analysis Results</h2>
                                <p><strong>Username:</strong> ${data.username}</p>
                                <p><strong>Repositories:</strong> ${data.repo_count}</p>
                                <p><strong>Followers:</strong> ${data.followers}</p>
                                <p><strong>Following:</strong> ${data.following}</p>
                                <p><strong>Total Stars:</strong> ${data.total_stars}</p>
                                <p><strong>Most Used Languages:</strong> ${data.top_languages.join(', ')}</p>
                                <p><strong>Account Created:</strong> ${data.created_at}</p>
                                <p><strong>Last Active:</strong> ${data.last_active}</p>
                            </div>
                        </div>
                    `;
                }
            } catch (error) {
                resultsDiv.innerHTML = '<div class="alert alert-danger">An error occurred while analyzing the profile.</div>';
            }
        });
    </script>
</body>
</html>
'''

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
        username = extract_username_from_url(github_url)
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
        
        for repo in repos:
            total_stars += repo.stargazers_count
            repo_langs = repo.get_languages()
            for lang, bytes_count in repo_langs.items():
                languages[lang] = languages.get(lang, 0) + bytes_count
        
        # Get top 5 languages
        top_languages = sorted(languages.items(), key=lambda x: x[1], reverse=True)[:5]
        top_languages = [lang for lang, _ in top_languages]
        
        return {
            **basic_info,
            'total_stars': total_stars,
            'top_languages': top_languages
        }
        
    except GithubException as e:
        if e.status == 404:
            raise ValueError("GitHub profile not found")
        elif e.status == 403:
            raise ValueError("API rate limit exceeded or authentication required")
        else:
            raise ValueError(f"GitHub API error: {str(e)}")

@app.route('/')
def home():
    """Render the home page."""
    return render_template_string(HTML_TEMPLATE)

@app.route('/analyze', methods=['POST'])
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
        return jsonify({'error': 'An unexpected error occurred'}), 500

if __name__ == '__main__':
    app.run(debug=True) 