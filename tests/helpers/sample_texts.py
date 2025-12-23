JD_TEXT_1 = """
Senior Backend Engineer

We are looking for an experienced backend engineer with:
- Strong Python programming skills
- SQL database experience (PostgreSQL preferred)
- Docker and containerization knowledge
- Experience with FastAPI or Django
- CI/CD pipeline experience

Nice to have:
- AWS or cloud experience
- Machine learning background
"""

# Resume that matches most JD skills
RESUME_TEXT_MATCH = """
John Doe
Backend Engineer

Skills:
- Python (5 years)
- SQL and PostgreSQL
- Docker and Kubernetes
- FastAPI framework
- AWS deployment

Experience:
Built scalable APIs using Python and FastAPI.
Managed PostgreSQL databases and wrote complex SQL queries.
Deployed applications using Docker containers.
"""

# Resume with partial match
RESUME_TEXT_PARTIAL = """
Jane Smith
Software Developer

Skills:
- Python programming
- JavaScript and React
- Basic SQL knowledge
- Git version control

Experience:
Full-stack development with focus on Python backend.
Some database work with SQL.
"""

# Empty resume
RESUME_TEXT_EMPTY = "   \n\n   \t   "

# Duplicate resume (same as match)
RESUME_TEXT_DUPLICATE = RESUME_TEXT_MATCH
