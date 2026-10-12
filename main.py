import pandas as pd
from RDG_with_config import RDG_with_config

if __name__ == "__main__":
    
    # Définir les chemins vers vos fichiers de configuration
    PERCENTAGE_FILE = 'pourcentages.csv'
    CONDITIONS_FILE = 'conditions.csv'

    print("--- 1. Initialisation de RDG_with_config depuis les fichiers ---")
    
    try:
        # On instancie la classe en lui passant les chemins des fichiers
        rdg_instance = RDG_with_config(
            percentage_filepath=PERCENTAGE_FILE, 
            conditions_filepath=CONDITIONS_FILE
        )
        print("\n✔️ Initialisation et validation de la configuration réussies.")
    except (Exception, FileNotFoundError) as e:
        print(f"\n❌ ERREUR lors de l'initialisation : {e}")
        exit()

    print("\n--- 2. Lancement de la génération de données ---")
    
    nombre_de_lignes_a_generer = 30
    # La méthode generate n'a pas besoin de changer
    donnees_generees_df = rdg_instance.generate(n=nombre_de_lignes_a_generer)

    print(f"\n--- 3. Vérification des {len(donnees_generees_df)} données générées ---")
    
    if donnees_generees_df is not None and not donnees_generees_df.empty:
        print("Affichage des 10 premières lignes :")
        print(donnees_generees_df.head(10))

        # Vérification des règles (comme dans l'exemple précédent)
        erreurs_règle1 = donnees_generees_df[(donnees_generees_df['ville'] == 'fes') & (donnees_generees_df['salaire'].astype(int) >= 15000)].shape[0]
        erreurs_règle2 = donnees_generees_df[(donnees_generees_df['categorie'] == 'A') & (donnees_generees_df['ville'] == 'casa')].shape[0]

        print("\nRésultat de la vérification :")
        if erreurs_règle1 == 0: print("✔️ Règle 1 (ville/salaire) respectée.")
        else: print(f"❌ ERREUR : {erreurs_règle1} violation(s) de la règle 1.")
        
        if erreurs_règle2 == 0: print("✔️ Règle 2 (categorie/ville) respectée.")
        else: print(f"❌ ERREUR : {erreurs_règle2} violation(s) de la règle 2.")