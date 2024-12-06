from .models import Subject, Topic

def populate_subjects_and_topics():
    # Define subjects with their corresponding topics
    subjects_data = {
        "Mathematics": [
            "Algebra", "Geometry", "Calculus", "Trigonometry", "Statistics", "Linear Algebra",
            "Number Theory", "Discrete Mathematics", "Probability", "Topology", "Differential Equations"
        ],
        "Science": [
            "Physics", "Chemistry", "Biology", "Astronomy", "Environmental Science", "Geology",
            "Ecology", "Botany", "Zoology", "Genetics", "Microbiology", "Biochemistry", "Biophysics"
        ],
        "Computer Science": [
            "Programming", "Algorithms", "Data Structures", "Artificial Intelligence", "Machine Learning",
            "Cybersecurity", "Network Engineering", "Web Development", "Database Systems", "Cloud Computing",
            "Data Science", "Software Engineering", "Computer Graphics", "Human-Computer Interaction"
        ],
        "Social Sciences": [
            "Psychology", "Sociology", "Anthropology", "Political Science", "Economics", "History",
            "Geography", "Archaeology", "Philosophy", "Law", "Criminology", "Demography"
        ],
        "Languages": [
            "English", "Spanish", "French", "German", "Mandarin", "Arabic", "Italian", "Japanese",
            "Russian", "Portuguese", "Linguistics", "Hindi", "Korean"
        ],
        "Literature": [
            "World Literature", "Poetry", "Drama", "Novel Studies", "Shakespeare", "Literary Criticism",
            "Comparative Literature", "Modern Literature", "Classical Literature"
        ],
        "Arts": [
            "Visual Arts", "Music", "Theater", "Dance", "Film Studies", "Graphic Design", "Photography",
            "Sculpture", "Art History", "Architecture", "Ceramics", "Painting"
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
        subject, created = Subject.objects.get_or_create(name=subject_name)
        subjects.append(subject)

    # Bulk create topics
    topics_to_create = []
    for subject_name, topic_list in subjects_data.items():
        subject = Subject.objects.get(name=subject_name)
        for topic_name in topic_list:
            topic, created = Topic.objects.get_or_create(
                name=topic_name, 
                subject=subject
            )
            topics_to_create.append(topic)
    print("Data populate successfully")
    return subjects, topics_to_create


