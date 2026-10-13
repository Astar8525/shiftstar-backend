import sys
from database import SessionLocal
import models

TABLES = [
    ("users", models.User),
    ("shifts", models.Shift),
    ("events", models.Event),
    ("production", models.ProductionData),
    ("history", models.ShiftHistory),
]


def count(db, model, company_id):
    return db.query(model).filter(model.company_id == company_id).count()


def main():
    args = sys.argv[1:]
    delete = "--delete" in args
    names = [a for a in args if not a.startswith("--")]
    db = SessionLocal()
    try:
        companies = db.query(models.Company).order_by(models.Company.id).all()
        print("COMPANIES (id | name | users | shifts | events | production | history)")
        for c in companies:
            counts = [count(db, m, c.id) for _, m in TABLES]
            print(c.id, "|", c.name, "|", " | ".join(str(n) for n in counts))
            emails = [u.email for u in db.query(models.User).filter(models.User.company_id == c.id).limit(6).all()]
            print("    members:", ", ".join(emails))
        if not delete:
            print("")
            print("Dry run only - nothing was deleted.")
            print('To delete, run: python cleanup_tests.py --delete "Company A" "Company B"')
            return
        if not names:
            print("No company names given - nothing deleted.")
            return
        targets = []
        for n in names:
            c = db.query(models.Company).filter(models.Company.name == n).first()
            if not c:
                print("Not found (exact name needed):", n)
                return
            targets.append(c)
        print("")
        print("WILL DELETE EVERYTHING FOR:", ", ".join(c.name for c in targets))
        if input("Type DELETE to confirm: ").strip() != "DELETE":
            print("Cancelled - nothing deleted.")
            return
        for c in targets:
            for _, m in reversed(TABLES):
                db.query(m).filter(m.company_id == c.id).delete(synchronize_session=False)
            db.delete(c)
        db.commit()
        print("Deleted.")
    finally:
        db.close()


if __name__ == "__main__":
    main()