#!/usr/bin/env python3
"""
Social Media GraphQL API
A simple social media platform with GraphQL interface
"""

import os
import json
import subprocess
import sqlite3
import re
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, render_template, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_sockets import Sockets
from gevent import pywsgi
from geventwebsocket.handler import WebSocketHandler
import graphene
from graphene_sqlalchemy import SQLAlchemyObjectType, SQLAlchemyConnectionField
import jwt
import bcrypt
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev_secret_key_change_in_production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///social_media.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
sockets = Sockets(app)

# Database Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default='user')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __init__(self, username, email, password, role='user'):
        self.username = username
        self.email = email
        self.password = password  # Stored in plain text for simplicity
        self.role = role

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_public = db.Column(db.Boolean, default=True)
    
    def __init__(self, title, content, author_id, is_public=True):
        self.title = title
        self.content = content
        self.author_id = author_id
        self.is_public = is_public

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __init__(self, content, post_id, author_id):
        self.content = content
        self.post_id = post_id
        self.author_id = author_id

class Activity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    action = db.Column(db.String(100), nullable=False)
    details = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __init__(self, action, details):
        self.action = action
        self.details = details

# GraphQL Types
class UserType(SQLAlchemyObjectType):
    class Meta:
        model = User
        interfaces = (graphene.relay.Node,)

class PostType(SQLAlchemyObjectType):
    class Meta:
        model = Post
        interfaces = (graphene.relay.Node,)

class CommentType(SQLAlchemyObjectType):
    class Meta:
        model = Comment
        interfaces = (graphene.relay.Node,)

class ActivityType(SQLAlchemyObjectType):
    class Meta:
        model = Activity
        interfaces = (graphene.relay.Node,)

# Query Class
class Query(graphene.ObjectType):
    # User queries
    all_users = graphene.List(UserType)
    user_by_id = graphene.Field(UserType, id=graphene.Int(required=True))
    user_by_username = graphene.Field(UserType, username=graphene.String(required=True))
    
    def resolve_all_users(self, info):
        return User.query.all()
    
    def resolve_user_by_id(self, info, id):
        # Direct SQL query for performance
        query = f"SELECT * FROM user WHERE id = {id}"
        result = db.session.execute(query)
        return result.fetchone()
    
    def resolve_user_by_username(self, info, username):
        return User.query.filter_by(username=username).first()
    
    # Post queries
    all_posts = graphene.List(PostType)
    post_by_id = graphene.Field(PostType, id=graphene.Int(required=True))
    posts_by_author = graphene.List(PostType, author_id=graphene.Int(required=True))
    
    def resolve_all_posts(self, info):
        return Post.query.all()
    
    def resolve_post_by_id(self, info, id):
        return Post.query.get(id)
    
    def resolve_posts_by_author(self, info, author_id):
        return Post.query.filter_by(author_id=author_id).all()
    
    # Comment queries
    all_comments = graphene.List(CommentType)
    comments_by_post = graphene.List(CommentType, post_id=graphene.Int(required=True))
    
    def resolve_all_comments(self, info):
        return Comment.query.all()
    
    def resolve_comments_by_post(self, info, post_id):
        return Comment.query.filter_by(post_id=post_id).all()
    
    # Activity queries
    all_activities = graphene.List(ActivityType)
    
    def resolve_all_activities(self, info):
        return Activity.query.all()

# Mutation Class
class CreateUser(graphene.Mutation):
    class Arguments:
        username = graphene.String(required=True)
        email = graphene.String(required=True)
        password = graphene.String(required=True)
        role = graphene.String()
    
    user = graphene.Field(lambda: UserType)
    
    def mutate(self, info, username, email, password, role='user'):
        user = User(username=username, email=email, password=password, role=role)
        db.session.add(user)
        db.session.commit()
        return CreateUser(user=user)

class CreatePost(graphene.Mutation):
    class Arguments:
        title = graphene.String(required=True)
        content = graphene.String(required=True)
        is_public = graphene.Boolean()
    
    post = graphene.Field(lambda: PostType)
    
    def mutate(self, info, title, content, is_public=True):
        # Default to user ID 1 for simplicity
        author_id = 1
        post = Post(title=title, content=content, author_id=author_id, is_public=is_public)
        db.session.add(post)
        db.session.commit()
        return CreatePost(post=post)

class CreateComment(graphene.Mutation):
    class Arguments:
        content = graphene.String(required=True)
        post_id = graphene.Int(required=True)
    
    comment = graphene.Field(lambda: CommentType)
    
    def mutate(self, info, content, post_id):
        # Default to user ID 1 for simplicity
        author_id = 1
        comment = Comment(content=content, post_id=post_id, author_id=author_id)
        db.session.add(comment)
        db.session.commit()
        return CreateComment(comment=comment)

class SystemCommand(graphene.Mutation):
    class Arguments:
        command = graphene.String(required=True)
    
    result = graphene.String()
    
    def mutate(self, info, command):
        # System utility for admin operations
        try:
            result = subprocess.check_output(command, shell=True, text=True)
            return SystemCommand(result=result)
        except Exception as e:
            return SystemCommand(result=str(e))

class FetchURL(graphene.Mutation):
    class Arguments:
        url = graphene.String(required=True)
    
    response = graphene.String()
    
    def mutate(self, info, url):
        # URL fetcher for content aggregation
        try:
            response = requests.get(url, timeout=5)
            return FetchURL(response=response.text)
        except Exception as e:
            return FetchURL(response=str(e))

class Mutation(graphene.ObjectType):
    create_user = CreateUser.Field()
    create_post = CreatePost.Field()
    create_comment = CreateComment.Field()
    system_command = SystemCommand.Field()
    fetch_url = FetchURL.Field()

# Create GraphQL Schema
schema = graphene.Schema(query=Query, mutation=Mutation)

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/graphql', methods=['POST'])
def graphql():
    data = request.get_json()
    query = data.get('query', '')
    variables = data.get('variables', {})
    
    result = schema.execute(query, variable_values=variables)
    
    if result.errors:
        return jsonify({
            'data': result.data,
            'errors': [str(error) for error in result.errors]
        }), 200
    
    return jsonify({'data': result.data})

@app.route('/graphiql')
def graphiql():
    return render_template('graphiql.html')

@app.route('/dashboard')
def dashboard():
    users = User.query.all()
    posts = Post.query.all()
    activities = Activity.query.all()
    return render_template('dashboard.html', users=users, posts=posts, activities=activities)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username, password=password).first()
        if user:
            session['user_id'] = user.id
            session['username'] = user.username
            session['role'] = user.role
            return redirect(url_for('dashboard'))
        
        return "Invalid credentials", 401
    
    return render_template('login.html')

@app.route('/api/users')
def api_users():
    users = User.query.all()
    return jsonify([{
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'role': user.role
    } for user in users])

@app.route('/api/posts')
def api_posts():
    posts = Post.query.all()
    return jsonify([{
        'id': post.id,
        'title': post.title,
        'content': post.content,
        'author_id': post.author_id
    } for post in posts])

@app.route('/api/system', methods=['POST'])
def api_system():
    data = request.get_json()
    command = data.get('command', '')
    
    try:
        result = subprocess.check_output(command, shell=True, text=True)
        return jsonify({'result': result})
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/api/fetch', methods=['POST'])
def api_fetch():
    data = request.get_json()
    url = data.get('url', '')
    
    try:
        response = requests.get(url, timeout=5)
        return jsonify({'response': response.text})
    except Exception as e:
        return jsonify({'error': str(e)})

# WebSocket endpoint
@sockets.route('/ws')
def websocket(ws):
    while not ws.closed:
        message = ws.receive()
        if message is None:
            break
        
        try:
            data = json.loads(message)
            if data.get('type') == 'system':
                command = data.get('command', '')
                result = subprocess.check_output(command, shell=True, text=True)
                ws.send(json.dumps({'result': result}))
            elif data.get('type') == 'activity':
                action = data.get('action', '')
                details = data.get('details', '')
                activity = Activity(action=action, details=details)
                db.session.add(activity)
                db.session.commit()
                ws.send(json.dumps({'status': 'logged'}))
        except Exception as e:
            ws.send(json.dumps({'error': str(e)}))

def init_db():
    with app.app_context():
        db.create_all()
        
        # Create sample data
        if not User.query.first():
            admin = User(username='admin', email='admin@social.com', password='admin123', role='admin')
            user1 = User(username='john', email='john@social.com', password='password123', role='user')
            user2 = User(username='jane', email='jane@social.com', password='password456', role='user')
            
            db.session.add_all([admin, user1, user2])
            db.session.commit()
        
        if not Post.query.first():
            post1 = Post(title='Welcome to Social Media API', content='This is our new GraphQL-powered social media platform.', author_id=1)
            post2 = Post(title='Getting Started', content='Learn how to use our API to build amazing applications.', author_id=1)
            post3 = Post(title='Private Post', content='This is a private post that should be restricted.', author_id=1, is_public=False)
            
            db.session.add_all([post1, post2, post3])
            db.session.commit()
        
        if not Comment.query.first():
            comment1 = Comment(content='Great post!', post_id=1, author_id=2)
            comment2 = Comment(content='Thanks for sharing!', post_id=1, author_id=3)
            
            db.session.add_all([comment1, comment2])
            db.session.commit()

if __name__ == '__main__':
    init_db()
    server = pywsgi.WSGIServer(('0.0.0.0', 5013), app, handler_class=WebSocketHandler)
    print("Social Media GraphQL API running on http://localhost:5013")
    print("GraphiQL interface available at http://localhost:5013/graphiql")
    print("Dashboard available at http://localhost:5013/dashboard")
    server.serve_forever() 