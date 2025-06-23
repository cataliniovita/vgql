# Social Media GraphQL API

A modern GraphQL-powered social media platform built with Flask and Graphene.

## Features

- **User Management**: Create and manage user accounts with role-based permissions
- **Content Management**: Create, read, and manage posts with public and private visibility
- **Comment System**: Enable user interactions with a robust commenting system
- **Real-time Updates**: WebSocket support for real-time features
- **GraphQL Interface**: Full GraphQL API with introspection enabled
- **Admin Dashboard**: Web-based administration panel

## Quick Start

### Prerequisites

- Python 3.7+
- pip

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd social-media-graphql-api
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
python app.py
```

4. Open your browser and navigate to:
   - **Home**: http://localhost:5013
   - **GraphiQL**: http://localhost:5013/graphiql
   - **Dashboard**: http://localhost:5013/dashboard
   - **Login**: http://localhost:5013/login

### Docker

You can also run the application using Docker:

```bash
# Build the image
docker build -t social-media-api .

# Run the container
docker run -p 5013:5013 social-media-api
```

## API Documentation

### GraphQL Endpoint

- **URL**: `POST /graphql`
- **GraphiQL**: Available at `/graphiql`

### Example Queries

#### Get all users
```graphql
query {
  allUsers {
    id
    username
    email
    role
  }
}
```

#### Get all posts
```graphql
query {
  allPosts {
    id
    title
    content
    authorId
    isPublic
  }
}
```

#### Create a new user
```graphql
mutation {
  createUser(
    username: "newuser"
    email: "newuser@example.com"
    password: "password123"
    role: "user"
  ) {
    user {
      id
      username
      email
      role
    }
  }
}
```

#### Create a new post
```graphql
mutation {
  createPost(
    title: "My First Post"
    content: "This is my first post using the API!"
    isPublic: true
  ) {
    post {
      id
      title
      content
      authorId
      isPublic
    }
  }
}
```

### REST API Endpoints

- `GET /api/users` - Get all users
- `GET /api/posts` - Get all posts
- `POST /api/system` - Execute system commands
- `POST /api/fetch` - Fetch URL content

### WebSocket

Connect to `/ws` for real-time features:

```javascript
const ws = new WebSocket('ws://localhost:5013/ws');

// Execute system command
ws.send(JSON.stringify({
  type: 'system',
  command: 'ls -la'
}));

// Log activity
ws.send(JSON.stringify({
  type: 'activity',
  action: 'user_login',
  details: 'User logged in successfully'
}));
```

## Default Data

The application comes with sample data:

### Users
- **admin** (admin@social.com) - Role: admin
- **john** (john@social.com) - Role: user
- **jane** (jane@social.com) - Role: user

### Posts
- Welcome to Social Media API
- Getting Started
- Private Post (not public)

## Development

### Project Structure

```
├── app.py              # Main application file
├── requirements.txt    # Python dependencies
├── templates/          # HTML templates
│   ├── index.html     # Landing page
│   ├── graphiql.html  # GraphiQL interface
│   ├── dashboard.html # Admin dashboard
│   └── login.html     # Login page
└── README.md          # This file
```

### Database

The application uses SQLite for simplicity. The database file (`social_media.db`) is created automatically on first run.

## Security Features

- Role-based access control
- Input validation and sanitization
- Secure password handling
- Rate limiting (planned)
- Query complexity analysis (planned)

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License. 