
from database import engine
from sqlalchemy import inspect

# Inspecter les tables de la base actuellement configurée
inspecteur = inspect(engine)

print("\n" + "=" * 60)
print("VÉRIFICATION DES TABLES")
print("=" * 60)

print("\nBase actuellement configurée :")
print(engine.url.render_as_string(hide_password=True))

for table in inspecteur.get_table_names():
    print(f"\nTable : {table}")

    colonnes = inspecteur.get_columns(table)

    for colonne in colonnes:
        print(f"  - {colonne['name']}")