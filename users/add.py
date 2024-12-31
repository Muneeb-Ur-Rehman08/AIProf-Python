from .models import Subject, Topic

def populate_subjects_and_topics():
    # Define subjects with their corresponding topics
    subjects_data = {
        "Mathematics": [
            "Algebra", "Geometry", "Calculus", "Trigonometry", "Statistics", "Linear Algebra",
            "Number Theory", "Discrete Mathematics", "Probability", "Topology", "Differential Equations",
            # Adding new topics
            "Arithmetic", "Addition", "Subtraction", "Multiplication", "Division", "Fractions",
            "Decimals", "Percentages", "Linear Equations", "Quadratic Equations", "Inequalities",
            "Polynomials", "Shapes", "Angles", "Theorems", "Coordinate Geometry", "Sine", "Cosine",
            "Tangent", "Pythagoras' Theorem", "Limits", "Derivatives", "Integrals", "Mean", "Median",
            "Mode", "Standard Deviation"
        ],
        "Science": [
            "Physics", "Chemistry", "Biology", "Astronomy", "Environmental Science", "Geology",
            "Ecology", "Botany", "Zoology", "Genetics", "Microbiology", "Biochemistry", "Biophysics",
            # Adding new topics
            "Newton's Laws of Motion", "Electricity", "Magnetism", "Thermodynamics", "Waves",
            "Quantum Mechanics", "Periodic Table", "Chemical Reactions", "Molecular Structure",
            "Acids and Bases", "Organic Chemistry", "Cell Structure", "Human Anatomy", "Evolution"
        ],
        "Computer Science": [
            "Programming", "Algorithms", "Data Structures", "Artificial Intelligence", "Machine Learning",
            "Cybersecurity", "Network Engineering", "Web Development", "Database Systems", "Cloud Computing",
            "Data Science", "Software Engineering", "Computer Graphics", "Human-Computer Interaction",
            # Adding new topics
            "Programming Basics", "Networking"
        ],
        "Social Sciences": [
            "Psychology", "Sociology", "Anthropology", "Political Science", "Economics", "History",
            "Geography", "Archaeology", "Philosophy", "Law", "Criminology", "Demography"
        ],
        "Languages": [
            "English", "Spanish", "French", "German", "Mandarin", "Arabic", "Italian", "Japanese",
            "Russian", "Portuguese", "Linguistics", "Hindi", "Korean"
        ],
        "English": [
            "Grammar", "Sentence Structure", "Tenses", "Vocabulary", "Writing Skills", "Essay Writing",
            "Creative Writing", "Literature", "Poetry Analysis", "Novel Studies", "Drama",
            "Research and Citation"
        ],
        "History": [
            "Ancient Civilizations", "Greek and Roman History", "Middle Ages", "Renaissance",
            "World Wars", "American Revolution", "Industrial Revolution", "Modern History",
            "Cold War", "Civil Rights Movement"
        ],
        "Geography": [
            "Physical Geography", "Landforms", "Weather and Climate", "Ecosystems",
            "Human Geography", "Population Studies", "Urbanization", "Economic Geography",
            "Global Trade"
        ],
        "Art": [
            "Visual Arts", "Music", "Theater", "Dance", "Film Studies", "Graphic Design", "Photography",
            "Sculpture", "Art History", "Architecture", "Ceramics", "Painting",
            # Adding new topics
            "Drawing Techniques", "Painting Styles", "Digital Art", "Design Principles"
        ],
        "Physical Education": [
            "Fitness Training", "Team Sports", "Individual Sports", "Health and Nutrition",
            "Mental Well-being", "Exercise Physiology"
        ],
        "Engineering": [
            "Mechanical Engineering", "Electrical Engineering", "Civil Engineering", "Chemical Engineering",
            "Aerospace Engineering", "Robotics", "Environmental Engineering", "Software Engineering",
            "Biomedical Engineering", "Industrial Engineering", "Materials Science"
        ],
        "Health Sciences": [
            "Anatomy", "Physiology", "Nutrition", "Public Health", "Medical Research", "Pharmacology",
            "Neuroscience", "Epidemiology", "Nursing", "Dentistry", "Veterinary Medicine"
        ],
        "Business": [
            "Management", "Marketing", "Finance", "Entrepreneurship", "Business Analytics",
            "International Business", "Supply Chain Management", "Human Resources", "Accounting"
        ],
        "Education": [
            "Early Childhood Education", "Elementary Education", "Secondary Education", "Higher Education",
            "Special Education", "Curriculum and Instruction", "Educational Psychology", "Educational Leadership"
        ],
        # Keeping the rest of the original subjects and their topics
        "Environmental Studies": [
            "Environmental Science", "Environmental Engineering", "Environmental Policy", "Sustainability",
            "Climate Change", "Conservation Biology"
        ],
        "Mathematics and Statistics": [
            "Statistics", "Probability", "Data Analysis", "Machine Learning", "Operations Research"
        ],
        "Physics": [
            "Classical Mechanics", "Electromagnetism", "Quantum Mechanics", "Thermodynamics",
            "Optics, Acoustics"
        ],
        "Chemistry": [
            "Organic Chemistry", "Inorganic Chemistry", "Physical Chemistry", "Analytical Chemistry"
        ],
        "Biology": [
            "Cellular Biology", "Molecular Biology", "Genetics", "Ecology", "Evolutionary Biology"
        ],
        "Computer Science and Engineering": [
            "Software Engineering", "Computer Networks", "Database Systems", "Artificial Intelligence",
            "Machine Learning", "Data Science"
        ],
        "Electrical Engineering": [
            "Circuit Theory", "Electronics", "Signal Processing", "Control Systems"
        ],
        "Mechanical Engineering": [
            "Mechanics of Materials", "Thermodynamics", "Fluid Mechanics", "Dynamics"
        ],
        "Civil Engineering": [
            "Structural Engineering", "Geotechnical Engineering", "Transportation Engineering",
            "Environmental Engineering"
        ]
    }

    # Bulk create subjects
    subjects = []
    for subject_name in subjects_data.keys():
        # Check if subject exists
        subject_exists = Subject.objects.filter(name=subject_name).exists()
        if not subject_exists:
            subject = Subject.objects.create(name=subject_name)
            subjects.append(subject)
            print(f"Created new subject: {subject_name}")

    # Bulk create topics
    topics_to_create = []
    for subject_name, topic_list in subjects_data.items():
        subject = Subject.objects.get(name=subject_name)
        for topic_name in topic_list:
            # Check if topic exists for this subject
            topic_exists = Topic.objects.filter(
                name=topic_name,
                subject=subject
            ).exists()
            
            if not topic_exists:
                topic = Topic.objects.create(
                    name=topic_name,
                    subject=subject
                )
                topics_to_create.append(topic)
                print(f"Created new topic: {topic_name} for subject: {subject_name}")

    print("Data population completed successfully")
    print(f"Added {len(subjects)} new subjects")
    print(f"Added {len(topics_to_create)} new topics")
    return subjects, topics_to_create


