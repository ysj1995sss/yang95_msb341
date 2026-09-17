"""
Representative job description fixtures for integration testing (Task 13).

These 10 descriptions are synthetic but realistic in structure and content —
they follow the format of real postings (Requirements / Preferred / Responsibilities
sections, "X+ years" phrasing, common skill/tool keywords) so they exercise the
JobAnalyzer's regex/heuristic extraction the same way real postings would.

Actual scraped job postings were not accessible in this environment, so these
stand in as realistic fixtures. They intentionally vary role type (engineering,
data, product, security, DevOps, etc.) and complexity (junior to staff/lead level,
short vs. long descriptions, sparse vs. dense keyword usage) to give the pipeline
a reasonably broad workout.
"""

JOB_DESCRIPTIONS = [
    # 1. Mid-level backend software engineer
    """
    Software Engineer, Backend

    We are looking for a Software Engineer to join our backend platform team.

    Requirements:
    - 3+ years of professional software development experience
    - Strong proficiency in Python
    - Experience building REST APIs
    - Familiarity with PostgreSQL or another relational database
    - Experience with Docker and containerized deployments

    Preferred:
    - Experience with Kubernetes
    - Familiarity with AWS
    - Exposure to microservices architecture

    Responsibilities:
    - Design and build backend services that power our core product
    - Write clean, tested, maintainable code
    - Collaborate with product and design on new features
    - Participate in code review and on-call rotation
    """,

    # 2. Senior data scientist
    """
    Senior Data Scientist

    Our analytics team is hiring a Senior Data Scientist to lead modeling
    efforts across the company.

    Requirements:
    - 5+ years of experience in data science or applied statistics
    - Strong Python skills, including pandas and scikit-learn
    - Experience with SQL and large-scale data warehouses
    - MS or PhD in a quantitative field (Statistics, CS, Math, or related)
    - Experience communicating findings to non-technical stakeholders

    Preferred:
    - Experience with deep learning frameworks (PyTorch or TensorFlow)
    - Experience with A/B testing and experimentation platforms
    - Familiarity with AWS or GCP

    Responsibilities:
    - Design and run experiments to evaluate product changes
    - Build predictive models for churn and lifetime value
    - Partner with engineering to productionize models
    - Mentor junior data scientists
    """,

    # 3. Product manager
    """
    Product Manager, Growth

    We're looking for a Product Manager to own our growth and onboarding
    experience.

    Requirements:
    - 4+ years of product management experience
    - Track record of shipping consumer-facing features
    - Strong analytical skills; comfortable with SQL
    - Experience working cross-functionally with engineering and design

    Preferred:
    - Experience with subscription or freemium business models
    - Background in growth marketing or lifecycle messaging
    - Familiarity with A/B testing frameworks

    Responsibilities:
    - Define and prioritize the growth roadmap
    - Write clear product requirements and success metrics
    - Run experiments to improve activation and retention
    - Partner with engineering, design, and data science
    """,

    # 4. Junior frontend developer
    """
    Junior Frontend Developer

    Great opportunity for an early-career developer to join a small,
    fast-moving product team.

    Requirements:
    - 1+ years of experience with JavaScript or TypeScript
    - Experience with React
    - Basic understanding of HTML/CSS and responsive design
    - Eagerness to learn and take feedback

    Nice to have:
    - Experience with Git and collaborative workflows
    - Exposure to REST APIs
    - Coursework or projects involving testing frameworks

    Responsibilities:
    - Build and maintain UI components
    - Fix bugs and implement small features under guidance from senior engineers
    - Participate in code review
    """,

    # 5. DevOps / Site Reliability Engineer
    """
    Site Reliability Engineer

    We need an SRE to help scale our infrastructure and improve reliability
    across our platform.

    Requirements:
    - 4+ years of experience in DevOps, SRE, or infrastructure engineering
    - Deep experience with Kubernetes and Docker in production
    - Experience with Terraform or similar infrastructure-as-code tools
    - Strong Linux systems knowledge
    - Experience with AWS

    Preferred:
    - Experience with observability tooling (Datadog, New Relic, Prometheus)
    - Scripting experience in Python or Go
    - Experience running on-call rotations and incident response

    Responsibilities:
    - Own uptime and reliability for core services
    - Build and maintain CI/CD pipelines
    - Automate infrastructure provisioning
    - Lead incident response and postmortems
    """,

    # 6. Machine learning engineer
    """
    Machine Learning Engineer

    Join our ML platform team building the infrastructure and models behind
    our recommendation system.

    Requirements:
    - 3+ years of experience building and deploying machine learning models
    - Strong Python skills
    - Experience with PyTorch or TensorFlow
    - Experience with distributed data processing (Spark or similar)
    - BS in Computer Science or equivalent experience

    Preferred:
    - Experience with recommendation systems or ranking models
    - Experience with Kubernetes for model serving
    - Familiarity with feature stores

    Responsibilities:
    - Design, train, and deploy ML models to production
    - Build data pipelines for feature engineering
    - Collaborate with data scientists on model evaluation
    - Monitor model performance and retrain as needed
    """,

    # 7. Security engineer
    """
    Security Engineer

    We are hiring a Security Engineer to strengthen our application and
    infrastructure security posture.

    Requirements:
    - 5+ years of experience in application or infrastructure security
    - Experience with threat modeling and secure code review
    - Familiarity with AWS security best practices
    - Experience with CI/CD pipeline security (SAST/DAST tooling)
    - Relevant certification preferred (CISSP, CCSP, or similar)

    Preferred:
    - Experience with Kubernetes security
    - Scripting ability in Python
    - Experience responding to security incidents

    Responsibilities:
    - Conduct security reviews of new features
    - Build automated security tooling into the CI/CD pipeline
    - Respond to and investigate security incidents
    - Partner with engineering teams on secure design
    """,

    # 8. Engineering manager (leadership)
    """
    Engineering Manager, Platform

    We're looking for an experienced Engineering Manager to lead our platform
    team of 6-8 engineers.

    Requirements:
    - 7+ years of software engineering experience, including 2+ years in
      a people management role
    - Track record of shipping backend or infrastructure systems
    - Strong experience with Python or Go
    - Experience with cloud infrastructure (AWS, GCP, or Azure)
    - Excellent communication and cross-functional collaboration skills

    Preferred:
    - Experience scaling engineering teams
    - Experience with Kubernetes and microservices architecture
    - MBA or equivalent leadership training

    Responsibilities:
    - Hire, coach, and grow a team of platform engineers
    - Set technical direction in partnership with senior ICs
    - Partner with product and other engineering teams on roadmap
    - Own team delivery and on-call health
    """,

    # 9. QA / Test automation engineer
    """
    QA Automation Engineer

    We need a QA Automation Engineer to build and maintain our automated
    test suites.

    Requirements:
    - 2+ years of experience in software quality assurance
    - Experience writing automated tests in Python or JavaScript
    - Familiarity with CI/CD tools (Jenkins, GitHub Actions, or similar)
    - Understanding of REST API testing

    Nice to have:
    - Experience with Selenium or Playwright
    - Experience with Docker
    - Familiarity with Agile/Scrum workflows

    Responsibilities:
    - Design and maintain automated regression test suites
    - Integrate tests into CI/CD pipelines
    - Work with engineers to triage and reproduce bugs
    - Report on quality metrics
    """,

    # 10. Sparse/short listing — full stack generalist at a small startup
    """
    Full Stack Engineer (Startup)

    Small startup looking for a generalist engineer who can move fast.

    Requirements:
    - Experience with JavaScript and Python
    - Comfortable working across the stack, frontend to backend
    - Startup experience a plus

    Responsibilities:
    - Ship features end to end
    - Wear many hats: engineering, some ops, some product
    - Work directly with the founders
    """,
]
