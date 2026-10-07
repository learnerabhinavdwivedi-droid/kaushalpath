"""Seed script for Phase 13: 300 synthetic is_demo conversations across 12 districts.

Used for testing small-group suppression (k >= 5), resistance analytics,
and scheme_admin broad visibility.
"""
from __future__ import annotations

import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add backend to path
REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.db.session import SessionLocal  # noqa: E402
from app.models.conversation import Conversation, ResistanceSnapshot, Turn  # noqa: E402
from app.models.student import Student  # noqa: E402
from app.models.user import User  # noqa: E402
from app.services.resistance import compute_resistance_score  # noqa: E402
from sqlalchemy import select  # noqa: E402

DISTRICTS = [
    ("Kanpur", "Uttar Pradesh", 35),
    ("Lucknow", "Uttar Pradesh", 35),
    ("Varanasi", "Uttar Pradesh", 30),
    ("Agra", "Uttar Pradesh", 25),
    ("Bhopal", "Madhya Pradesh", 35),
    ("Indore", "Madhya Pradesh", 30),
    ("Jaipur", "Rajasthan", 30),
    ("Patna", "Bihar", 30),
    ("Ranchi", "Jharkhand", 25),
    ("Pune", "Maharashtra", 20),
    ("Aligarh", "Uttar Pradesh", 3),   # Small bucket for suppression testing (< 5)
    ("Nagpur", "Maharashtra", 2),      # Small bucket for suppression testing (< 5)
]

TOPICS = ["income", "security", "cost", "safety", "distance", "social", "other"]

SAMPLE_TURNS = {
    "income": [
        ("parent", "इस ट्रेड में शुरुआत में कितनी तनख्वाह मिलेगी?", "hi", "negative", 0.6),
        ("assistant", "NCVET के अनुसार औसत मासिक वेतन ₹18,000 है।", "hi", "neutral", 0.0),
        ("parent", "अगर समय के साथ वेतन बढ़ता है तो ठीक है।", "hi", "positive", 0.2),
    ],
    "safety": [
        ("parent", "लड़कियों के लिए वर्कशॉप में सुरक्षा का क्या प्रबंध है?", "hi", "negative", 0.8),
        ("assistant", "केंद्र में महिला प्रशिक्षक और सीसीटीवी सुरक्षा उपलब्ध है।", "hi", "neutral", 0.0),
        ("parent", "हॉस्टल की सुरक्षा देखकर हम आश्वस्त हैं।", "hi", "positive", 0.3),
    ],
    "cost": [
        ("parent", "हम ज्यादा फीस नहीं दे सकते, खर्चा कितना होगा?", "hi", "negative", 0.7),
        ("assistant", "सरकारी फीस ₹4,500 है और वजीफा भी मिलता है।", "hi", "neutral", 0.0),
        ("learner", "मैं स्कॉलरशिप के लिए आवेदन कर दूंगा।", "hi", "positive", 0.1),
    ],
    "security": [
        ("parent", "क्या कोर्स पूरा होने के बाद पक्की नौकरी मिलती है?", "hi", "negative", 0.5),
        ("assistant", "संस्थान का प्लेसमेंट प्रतिशत 82% है।", "hi", "neutral", 0.0),
        ("parent", "यह जानकर अच्छा लगा कि प्लेसमेंट अच्छा है।", "hi", "positive", 0.2),
    ],
    "distance": [
        ("parent", "सेंटर घर से बहुत दूर है, आने जाने में दिक्कत होगी।", "hi", "negative", 0.6),
        ("assistant", "केंद्र तक सीधी बस सेवा और हॉस्टल की व्यवस्था है।", "hi", "neutral", 0.0),
        ("parent", "बस की सुविधा है तो ठीक रहेगा।", "hi", "neutral", 0.1),
    ],
    "social": [
        ("parent", "रिश्तेदार कहते हैं कि आईटीआई की कोई इज्जत नहीं है।", "hi", "negative", 0.7),
        ("assistant", "NSQF प्रमाणन राष्ट्रीय स्तर पर मान्य तकनीकी योग्यता है।", "hi", "neutral", 0.0),
        ("parent", "सरकारी मान्यता है तो हम सहमत हैं।", "hi", "positive", 0.3),
    ],
    "other": [
        ("learner", "एडमिशन के लिए कौन से दस्तावेज चाहिए?", "hi", "neutral", 0.1),
        ("assistant", "दसवीं की मार्कशीट और आधार कार्ड आवश्यक है।", "hi", "neutral", 0.0),
    ],
}


def seed_demo_conversations() -> int:
    db = SessionLocal()
    try:
        # Find an existing student or create a synthetic demo pool
        existing_students = db.scalars(select(Student)).all()
        if not existing_students:
            print("No existing students found. Creating demo student...")
            user = User(
                email=f"demo_stu_{random.randint(1000, 9999)}@example.com",
                hashed_password="pw",
                role="student",
                lang="hi",
            )
            db.add(user)
            db.flush()
            student = Student(
                user_id=user.id,
                district="Kanpur",
                state="Uttar Pradesh",
                edu_level="10th",
                budget_band="low",
                relocate_ok=True,
                language="hi",
            )
            db.add(student)
            db.commit()
            existing_students = [student]

        base_date = datetime.now() - timedelta(days=30)
        total_seeded = 0

        # Delete any previous demo conversations to keep idempotent
        # Identified by synthetic prefix or created during seed
        print("Clearing previous demo conversations...")
        old_convs = db.scalars(
            select(Conversation).where(Conversation.lang == "demo_seeded")
        ).all()
        for oc in old_convs:
            db.delete(oc)
        db.commit()

        print("Seeding 300 demo conversations across 12 districts...")
        target_student_map = {}

        # Create 1 student per district to represent the district cleanly
        for dist, st, _target_count in DISTRICTS:
            user = User(
                email=f"demo_{dist.lower()}_{random.randint(10000, 99999)}@example.com",
                hashed_password="pw",
                role="student",
                lang="hi",
            )
            db.add(user)
            db.flush()
            stu = Student(
                user_id=user.id,
                district=dist,
                state=st,
                edu_level="10th",
                budget_band="low",
                relocate_ok=False,
                language="hi",
            )
            db.add(stu)
            db.flush()
            target_student_map[dist] = stu

        # Generate conversations
        for dist, _st, target_count in DISTRICTS:
            stu = target_student_map[dist]
            for _i in range(target_count):
                topic = random.choice(TOPICS)
                delta_days = random.randint(0, 28)
                delta_hours = random.randint(1, 23)
                c_date = base_date + timedelta(days=delta_days, hours=delta_hours)
                conv = Conversation(
                    student_id=stu.id,
                    room_id=None,
                    lang="hi",
                    status="active",
                    created_at=c_date,
                    updated_at=c_date,
                )
                db.add(conv)
                db.flush()

                # Add turns
                script = SAMPLE_TURNS.get(topic, SAMPLE_TURNS["other"])
                for idx, (spk, txt, lng, sent, inten) in enumerate(script):
                    turn = Turn(
                        conversation_id=conv.id,
                        speaker=spk,
                        text=txt,
                        lang=lng,
                        intent="inquire" if sent != "negative" else "object",
                        topic=topic,
                        sentiment=sent,
                        intensity=inten,
                        facts_json=None,
                        fallback_used=False,
                        created_at=c_date + timedelta(minutes=idx * 2),
                        updated_at=c_date + timedelta(minutes=idx * 2),
                    )
                    db.add(turn)
                    db.flush()

                    # Record Rs snapshot
                    rs = compute_resistance_score(
                        topic=topic,
                        sentiment=sent,
                        intensity=inten,
                        conversation=conv,
                        db=db,
                    )
                    snap = ResistanceSnapshot(
                        conversation_id=conv.id,
                        turn_id=turn.id,
                        rs=rs,
                        created_at=turn.created_at,
                        updated_at=turn.created_at,
                    )
                    db.add(snap)

                total_seeded += 1

        db.commit()
        msg = f"Successfully seeded {total_seeded} conversations across {len(DISTRICTS)} districts!"
        print(msg)
        return total_seeded
    finally:
        db.close()


if __name__ == "__main__":
    count = seed_demo_conversations()
    print(f"Done. Seeded {count} conversations.")
