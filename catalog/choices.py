"""Fields of education from UNESCO's ISCED-F 2013.

A course's area is an ISCED-F detailed field (four-digit code). Its broad field follows from the code.
'Not further defined' codes are left out; 'inter-disciplinary' (xx88) and 'not elsewhere classified'
codes are kept where they are useful for university courses.
"""
from django.db import models


class FieldOfStudy(models.TextChoices):
    EDUCATION = "education", "Education"
    ARTS = "arts", "Arts & humanities"
    SOCIAL = "social", "Social sciences, journalism & information"
    BUSINESS = "business", "Business, administration & law"
    NATURAL = "natural", "Natural sciences, mathematics & statistics"
    ICT = "ict", "Information & communication technologies"
    ENGINEERING = "engineering", "Engineering, manufacturing & construction"
    AGRICULTURE = "agriculture", "Agriculture, forestry, fisheries & veterinary"
    HEALTH = "health", "Health & welfare"
    SERVICES = "services", "Services"


_DETAILED_FIELDS = {
    FieldOfStudy.EDUCATION: [
        ("0111", "Education science"),
        ("0112", "Training for pre-school teachers"),
        ("0113", "Teacher training without subject specialisation"),
        ("0114", "Teacher training with subject specialisation"),
        ("0188", "Inter-disciplinary programmes involving education"),
    ],
    FieldOfStudy.ARTS: [
        ("0211", "Audio-visual techniques and media production"),
        ("0212", "Fashion, interior and industrial design"),
        ("0213", "Fine arts"),
        ("0214", "Handicrafts"),
        ("0215", "Music and performing arts"),
        ("0221", "Religion and theology"),
        ("0222", "History and archaeology"),
        ("0223", "Philosophy and ethics"),
        ("0231", "Language acquisition"),
        ("0232", "Literature and linguistics"),
        ("0288", "Inter-disciplinary programmes involving arts and humanities"),
    ],
    FieldOfStudy.SOCIAL: [
        ("0311", "Economics"),
        ("0312", "Political sciences and civics"),
        ("0313", "Psychology"),
        ("0314", "Sociology and cultural studies"),
        ("0321", "Journalism and reporting"),
        ("0322", "Library, information and archival studies"),
        ("0388", "Inter-disciplinary programmes involving social sciences, journalism and information"),
    ],
    FieldOfStudy.BUSINESS: [
        ("0411", "Accounting and taxation"),
        ("0412", "Finance, banking and insurance"),
        ("0413", "Management and administration"),
        ("0414", "Marketing and advertising"),
        ("0415", "Secretarial and office work"),
        ("0416", "Wholesale and retail sales"),
        ("0417", "Work skills"),
        ("0421", "Law"),
        ("0488", "Inter-disciplinary programmes involving business, administration and law"),
    ],
    FieldOfStudy.NATURAL: [
        ("0511", "Biology"),
        ("0512", "Biochemistry"),
        ("0521", "Environmental sciences"),
        ("0522", "Natural environments and wildlife"),
        ("0531", "Chemistry"),
        ("0532", "Earth sciences"),
        ("0533", "Physics"),
        ("0541", "Mathematics"),
        ("0542", "Statistics"),
        ("0588", "Inter-disciplinary programmes involving natural sciences, mathematics and statistics"),
    ],
    FieldOfStudy.ICT: [
        ("0611", "Computer use"),
        ("0612", "Database and network design and administration"),
        ("0613", "Software and applications development and analysis"),
        ("0619", "ICTs not elsewhere classified"),
        ("0688", "Inter-disciplinary programmes involving ICTs"),
    ],
    FieldOfStudy.ENGINEERING: [
        ("0711", "Chemical engineering and processes"),
        ("0712", "Environmental protection technology"),
        ("0713", "Electricity and energy"),
        ("0714", "Electronics and automation"),
        ("0715", "Mechanics and metal trades"),
        ("0716", "Motor vehicles, ships and aircraft"),
        ("0721", "Food processing"),
        ("0722", "Materials (glass, paper, plastic and wood)"),
        ("0723", "Textiles (clothes, footwear and leather)"),
        ("0724", "Mining and extraction"),
        ("0731", "Architecture and town planning"),
        ("0732", "Building and civil engineering"),
        ("0788", "Inter-disciplinary programmes involving engineering, manufacturing and construction"),
    ],
    FieldOfStudy.AGRICULTURE: [
        ("0811", "Crop and livestock production"),
        ("0812", "Horticulture"),
        ("0821", "Forestry"),
        ("0831", "Fisheries"),
        ("0841", "Veterinary"),
        ("0888", "Inter-disciplinary programmes involving agriculture, forestry, fisheries and veterinary"),
    ],
    FieldOfStudy.HEALTH: [
        ("0911", "Dental studies"),
        ("0912", "Medicine"),
        ("0913", "Nursing and midwifery"),
        ("0914", "Medical diagnostic and treatment technology"),
        ("0915", "Therapy and rehabilitation"),
        ("0916", "Pharmacy"),
        ("0917", "Traditional and complementary medicine and therapy"),
        ("0921", "Care of the elderly and of disabled adults"),
        ("0922", "Child care and youth services"),
        ("0923", "Social work and counselling"),
        ("0988", "Inter-disciplinary programmes involving health and welfare"),
    ],
    FieldOfStudy.SERVICES: [
        ("1011", "Domestic services"),
        ("1012", "Hair and beauty services"),
        ("1013", "Hotel, restaurants and catering"),
        ("1014", "Sports"),
        ("1015", "Travel, tourism and leisure"),
        ("1021", "Community sanitation"),
        ("1022", "Occupational health and safety"),
        ("1031", "Military and defence"),
        ("1032", "Protection of persons and property"),
        ("1041", "Transport services"),
        ("1088", "Inter-disciplinary programmes involving services"),
    ],
}

# Grouped choices for forms: the broad field is the group heading, the detailed field the option.
AREA_CHOICES = [(f.label, [(code, f"{code} {name}") for code, name in items]) for f, items in _DETAILED_FIELDS.items()]
AREA_NAMES = {code: name for items in _DETAILED_FIELDS.values() for code, name in items}
AREA_TO_FIELD = {code: f.value for f, items in _DETAILED_FIELDS.items() for code, _ in items}
