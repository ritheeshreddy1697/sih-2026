# Approved localized copy is intentionally kept as complete lines.
# ruff: noqa: E501

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import CareerFaq, CareerLanguage, User

FAQ_CONTENT: tuple[tuple[str, str, str, str, list[str], str], ...] = (
    (
        "programmes",
        "programme",
        "How do I find a suitable training programme?",
        "Use the Programmes page to compare only published programmes. Check the stated eligibility, language, location, available capacity and application deadline on the programme record before applying.",
        ["programme", "training", "course", "eligibility", "apply"],
        "/programmes",
    ),
    (
        "jobs",
        "job",
        "How are jobs matched to my profile?",
        "The Employment Exchange compares published jobs from verified employers with your verified skills, course certificates, interests and preferred location. Open each job to review the match reasons and requirements.",
        ["job", "employment", "verified skills", "match", "vacancy"],
        "/employment",
    ),
    (
        "resume",
        "resume",
        "How should I prepare my resume?",
        "Keep the resume concise. Include a short summary, education, relevant experience, verified NCCT skills and measurable achievements. Tailor it to the published job and do not include sensitive identity or banking numbers.",
        ["resume", "cv", "skills", "experience"],
        "/employment",
    ),
    (
        "interview",
        "interview",
        "How can I prepare for an interview?",
        "Read the actual job description, prepare examples using situation, task, action and result, and practise explaining your verified skills. Confirm interview details only through the Employment Exchange record or the verified employer.",
        ["interview", "prepare", "questions", "practice"],
        "/employment",
    ),
    (
        "entrepreneurship",
        "entrepreneurship",
        "How do I explore cooperative entrepreneurship?",
        "Start with a clearly defined member need, member participation, governance roles, a basic market and cost assessment, and a transparent operating plan. This counsellor does not claim eligibility for government schemes; ask human support for programme-specific guidance.",
        ["cooperative", "entrepreneurship", "enterprise", "business", "scheme"],
        "/career-counsellor",
    ),
    (
        "navigation",
        "navigation",
        "Where can I find my learning and certificates?",
        "Open Learning for lessons and assessments, Certificates for your skill wallet, Programmes for applications, and Employment Exchange for jobs and application status.",
        ["where", "learning", "certificate", "page", "navigate"],
        "/dashboard",
    ),
    (
        "programmes",
        "programme",
        "मेरे लिए उपयुक्त प्रशिक्षण कार्यक्रम कैसे खोजें?",
        "केवल प्रकाशित कार्यक्रमों की तुलना करने के लिए कार्यक्रम पेज खोलें। आवेदन से पहले कार्यक्रम रिकॉर्ड में दी गई पात्रता, भाषा, स्थान, उपलब्ध क्षमता और अंतिम तिथि जाँचें।",
        ["कार्यक्रम", "प्रशिक्षण", "पाठ्यक्रम", "योग्यता", "आवेदन"],
        "/programmes",
    ),
    (
        "jobs",
        "job",
        "मेरी प्रोफ़ाइल से नौकरियों का मिलान कैसे होता है?",
        "रोज़गार विनिमय सत्यापित नियोक्ताओं की प्रकाशित नौकरियों का मिलान आपके सत्यापित कौशल, पाठ्यक्रम प्रमाणपत्र, रुचियों और पसंदीदा स्थान से करता है। कारण और आवश्यकताएँ देखने के लिए नौकरी खोलें।",
        ["नौकरी", "रोज़गार", "कौशल", "मिलान", "रिक्ति"],
        "/employment",
    ),
    (
        "resume",
        "resume",
        "रिज़्यूमे कैसे तैयार करूँ?",
        "रिज़्यूमे संक्षिप्त रखें। छोटा परिचय, शिक्षा, संबंधित अनुभव, सत्यापित NCCT कौशल और मापने योग्य उपलब्धियाँ जोड़ें। प्रकाशित नौकरी के अनुसार इसे बदलें और पहचान या बैंक की संवेदनशील जानकारी न दें।",
        ["रिज्यूमे", "बायोडाटा", "कौशल", "अनुभव"],
        "/employment",
    ),
    (
        "interview",
        "interview",
        "साक्षात्कार की तैयारी कैसे करूँ?",
        "वास्तविक नौकरी विवरण पढ़ें, परिस्थिति, कार्य, कार्रवाई और परिणाम के क्रम में उदाहरण तैयार करें, और अपने सत्यापित कौशल समझाने का अभ्यास करें। विवरण केवल रोज़गार विनिमय रिकॉर्ड या सत्यापित नियोक्ता से पक्का करें।",
        ["साक्षात्कार", "इंटरव्यू", "तैयारी", "अभ्यास"],
        "/employment",
    ),
    (
        "entrepreneurship",
        "entrepreneurship",
        "सहकारी उद्यमिता कैसे शुरू करूँ?",
        "पहले सदस्यों की स्पष्ट आवश्यकता, सदस्य भागीदारी, शासन की भूमिकाएँ, बाजार और लागत का बुनियादी आकलन तथा पारदर्शी संचालन योजना तैयार करें। यह काउंसलर किसी सरकारी योजना की पात्रता का दावा नहीं करता; विशेष मार्गदर्शन के लिए मानव सहायता लें।",
        ["सहकारी", "उद्यम", "व्यवसाय", "योजना"],
        "/career-counsellor",
    ),
    (
        "navigation",
        "navigation",
        "मेरी लर्निंग और प्रमाणपत्र कहाँ मिलेंगे?",
        "पाठ और आकलन के लिए लर्निंग, कौशल वॉलेट के लिए प्रमाणपत्र, आवेदन के लिए कार्यक्रम और नौकरियों तथा आवेदन स्थिति के लिए रोज़गार विनिमय खोलें।",
        ["कहाँ", "लर्निंग", "प्रमाणपत्र", "पेज"],
        "/dashboard",
    ),
    (
        "programmes",
        "programme",
        "నాకు సరిపోయే శిక్షణ కార్యక్రమాన్ని ఎలా కనుగొనాలి?",
        "ప్రచురించిన కార్యక్రమాలను పోల్చడానికి శిక్షణల పేజీని ఉపయోగించండి. దరఖాస్తు ముందు కార్యక్రమ రికార్డులోని అర్హత, భాష, ప్రదేశం, అందుబాటులో ఉన్న సీట్లు మరియు చివరి తేదీని తనిఖీ చేయండి.",
        ["కార్యక్రమం", "శిక్షణ", "కోర్సు", "అర్హత", "దరఖాస్తు"],
        "/programmes",
    ),
    (
        "jobs",
        "job",
        "నా ప్రొఫైల్‌కు ఉద్యోగాలు ఎలా సరిపోలుతాయి?",
        "ఉపాధి వేదిక ధృవీకరించిన యజమానుల ప్రచురించిన ఉద్యోగాలను మీ ధృవీకరించిన నైపుణ్యాలు, కోర్సు సర్టిఫికెట్లు, ఆసక్తులు మరియు ప్రాధాన్య ప్రదేశంతో పోలుస్తుంది. కారణాలు మరియు అవసరాల కోసం ఉద్యోగాన్ని తెరవండి.",
        ["ఉద్యోగం", "ఉపాధి", "నైపుణ్యాలు", "సరిపోలిక", "ఖాళీ"],
        "/employment",
    ),
    (
        "resume",
        "resume",
        "రెజ్యూమేను ఎలా సిద్ధం చేయాలి?",
        "రెజ్యూమేను సంక్షిప్తంగా ఉంచండి. చిన్న పరిచయం, విద్య, సంబంధిత అనుభవం, ధృవీకరించిన NCCT నైపుణ్యాలు మరియు కొలవగల విజయాలను చేర్చండి. ప్రచురించిన ఉద్యోగానికి అనుగుణంగా మార్చండి; సున్నితమైన గుర్తింపు లేదా బ్యాంకు వివరాలు చేర్చవద్దు.",
        ["రెజ్యూమే", "సీవీ", "నైపుణ్యాలు", "అనుభవం"],
        "/employment",
    ),
    (
        "interview",
        "interview",
        "ఇంటర్వ్యూకు ఎలా సిద్ధం కావాలి?",
        "అసలు ఉద్యోగ వివరణ చదవండి, పరిస్థితి, పని, చర్య, ఫలితం పద్ధతిలో ఉదాహరణలు సిద్ధం చేయండి మరియు మీ ధృవీకరించిన నైపుణ్యాలను వివరించడం సాధన చేయండి. వివరాలను ఉపాధి వేదిక రికార్డు లేదా ధృవీకరించిన యజమాని ద్వారా మాత్రమే నిర్ధారించండి.",
        ["ఇంటర్వ్యూ", "సిద్ధం", "ప్రశ్నలు", "సాధన"],
        "/employment",
    ),
    (
        "entrepreneurship",
        "entrepreneurship",
        "సహకార వ్యవస్థలో వ్యాపారాన్ని ఎలా ప్రారంభించాలి?",
        "ముందుగా సభ్యుల స్పష్టమైన అవసరం, సభ్యుల భాగస్వామ్యం, పాలనా పాత్రలు, ప్రాథమిక మార్కెట్ మరియు ఖర్చు అంచనా, పారదర్శక నిర్వహణ ప్రణాళిక సిద్ధం చేయండి. ఈ కౌన్సెలర్ ప్రభుత్వ పథకాల అర్హతను నిర్ధారించదు; ప్రత్యేక మార్గదర్శకత్వం కోసం మానవ సహాయం కోరండి.",
        ["సహకార", "వ్యాపారం", "ఎంటర్‌ప్రైజ్", "పథకం"],
        "/career-counsellor",
    ),
    (
        "navigation",
        "navigation",
        "నా లెర్నింగ్ మరియు సర్టిఫికెట్లు ఎక్కడ కనిపిస్తాయి?",
        "పాఠాలు మరియు అంచనాల కోసం లెర్నింగ్, స్కిల్ వాలెట్ కోసం సర్టిఫికెట్లు, దరఖాస్తుల కోసం శిక్షణలు, ఉద్యోగాలు మరియు దరఖాస్తు స్థితి కోసం ఉపాధి వేదికను తెరవండి.",
        ["ఎక్కడ", "లెర్నింగ్", "సర్టిఫికెట్", "పేజీ"],
        "/dashboard",
    ),
)


def seed_career_faqs(db: Session, approver: User) -> None:
    languages = (CareerLanguage.ENGLISH, CareerLanguage.HINDI, CareerLanguage.TELUGU)
    for index, (slug, category, question, answer, keywords, platform_url) in enumerate(FAQ_CONTENT):
        language = languages[index // 6]
        faq = db.scalar(
            select(CareerFaq).where(
                CareerFaq.slug == slug,
                CareerFaq.language == language,
            )
        )
        if faq is None:
            faq = CareerFaq(slug=slug, language=language, category=category)
            db.add(faq)
        faq.question = question
        faq.answer = answer
        faq.keywords = keywords
        faq.platform_url = platform_url
        faq.is_approved = True
        faq.approved_by_id = approver.id
