from Field import Field, parse_condition
import random
import pandas as pd
import time
import copy
import os



""" RDG_with_config (Random Data Generation With Configuration) est le cœur de notre projet de génération de données. Cette
classe est conçue pour fournir une interface puissante et flexible permettant de générer des ensembles de données conformes 
aux spécifications de l'utilisateur. En combinant les informations fournies par les fichiers de paramètres et de conditions,
ainsi que les intervalles de pourcentage.
"""
class RDG_with_config:
    
    def __init__(self, percentage_filepath, conditions_filepath=None):
        """
        Constructeur qui charge la configuration depuis des fichiers.
        Args:
            percentage_filepath (str): Chemin vers le fichier CSV des pourcentages.
            conditions_filepath (str, optional): Chemin vers le fichier CSV des conditions.
        """
        # 1. Charger le fichier des pourcentages
        try:
            self.df = pd.read_csv(percentage_filepath)
        except FileNotFoundError:
            raise FileNotFoundError(f"Le fichier de pourcentages '{percentage_filepath}' est introuvable.")

        self.Fields = []
        
        # 2. Charger le fichier de conditions (s'il est fourni)
        self.conditions_data = None
        if conditions_filepath:
            try:
                self.conditions_data = pd.read_csv(conditions_filepath)
            except FileNotFoundError:
                print(f"AVERTISSEMENT : Le fichier de conditions '{conditions_filepath}' est introuvable. Génération sans contraintes.")

        # 3. Parser les contraintes une seule fois
        self.parsed_constraints = []
        if self.conditions_data is not None:
            # On utilise les noms de colonnes plus clairs : if_condition, then_not_condition
            for _, row in self.conditions_data.iterrows():
                if_cond = parse_condition(row['field'])
                
                list_conditions_interdites = row['conditions'].split("#")
                for then_not_str in list_conditions_interdites:
                    self.parsed_constraints.append({
                        'if': if_cond,
                        'then_not': parse_condition(then_not_str)
                    })
        
        # 4. Lancer l'initialisation des champs
        self.initialize_fields()



    # def initialize_fields(self):
    #     column_names = list(self.df.columns)
        
    #     # Le reste de votre code utilise `self.df` qui est maintenant peuplé depuis le CSV
    #     data_list = [self.df[column].dropna().astype(str).tolist() for column in self.df.columns]

    #     # Étape 1: Créer tous les objets Field et les valider
    #     for i in range(len(column_names)):
    #         field = Field(column_names[i])
    #         field.fill_map(data_list[i])
    #         self.Fields.append(field)
            
    #     # Étape 2: Donner à chaque Field le contexte global
    #     all_distributions = {f.name: f._base_percentage_dist for f in self.Fields}
    #     for field in self.Fields:
    #         field.link_global_context_to_percentage_dict(self.parsed_constraints, all_distributions)
            
            
    """
    Cette méthode prend en charge l'initialisation des instances de la classe Field pour chaque colonne dans l'attribut df. Elle 
    parcourt chaque colonne du DataFrame df et crée un objet Field correspondant pour stocker les informations spécifiques à 
    chaque variable. Ces objets Field sont ensuite ajoutés à la liste Fields de l'instance de RDG_with_config, permettant ainsi 
    de stocker et de gérer toutes les variables du DataFrame de manière organisée.
    """
    def initialize_fields(self):
        column_names = list(self.df.columns)
        
        data_list = [self.df[column].dropna().tolist() for column in self.df.columns]

        k = len(column_names)
        for i in range(k):
            self.Fields.append(Field(column_names[i]))
            self.Fields[i].fill_map(data_list[i])


        #modif2
        # On collecte toutes les distributions de base dans un dictionnaire
        all_distributions = {f.name: f._base_percentage_dist for f in self.Fields}
        
        # On passe ce "cerveau collectif" et les règles à chaque objet Field
        for field in self.Fields:
            field.link_global_context_to_percentage_dict(self.parsed_constraints, all_distributions)

        #fin modif2
          
    
    """
    cette méthode orchestre la génération de données aléatoires en respectant les paramètres et les configurations fournies par 
    l'utilisateur. En utilisant des méthodes internes telles que SplitInterval pour choisir aléatoirement les valeurs, 
    PercentageCondition pour gérer les conditions basées sur des pourcentages, et check_condition pour vérifier la conformité des 
    données générées, cette méthode assure la cohérence et la pertinence des données produites. Enfin, elle stocke les données 
    générées dans un fichier si un nom de fichier est spécifié, offrant ainsi une flexibilité supplémentaire dans la manipulation
    et la sauvegarde des données générées.
    """
    def generate_random_data(self,n,filename=None):
        
        nombre_donnees = 0 # Nombre de données à générer
        donnees_generees = []
        FieldsCp = copy.deepcopy(self.Fields)
        reset = 0
        
        while nombre_donnees <n:
            donnee = {}
            for field_obj in FieldsCp:
                #modif3
                field_obj.reset_context_for_new_line()
                #fin modif3

            # Maintenant, on commence à construire la ligne
            for obj in FieldsCp:
                obj.update_percentage_context(donnee)    
                while True :    
                    if(not obj.percentage ):
                        break
                    attribut=self.SplitInterval(obj)
                    if(self.PercentageCondition(obj,attribut,donnees_generees,FieldsCp,n)):
                        donnee[obj.name] = str(attribut)
                        break
                
            
            if not self.check_condition(donnee) :
                reset = 0
                donnees_generees.append(donnee)
                
                nombre_donnees+=1
                print(nombre_donnees)
            else:
                reset+=1
                if(reset==500):
                    break
        #print(pd.DataFrame(donnees_generees)['age'])
        if(filename):
            if not os.path.isfile(filename):
                pd.DataFrame(donnees_generees).to_csv(filename,index=False)
            else:
                pd.DataFrame(donnees_generees).to_csv(filename,mode='a', index=False,header=False)
        else :
            return pd.DataFrame(donnees_generees)

        

    
    """
    Cette méthode prend une ligne de données représentée sous forme de dictionnaire en tant que paramètre et vérifie si cette 
    ligne satisfait les conditions spécifiées dans l'attribut conditions_data. Elle parcourt les conditions spécifiées dans 
    conditions_data et compare les valeurs dans la ligne de données avec les conditions pour chaque variable. Si toutes les 
    conditions sont satisfaites pour toutes les variables, la méthode renvoie True, sinon elle renvoie False. Cette méthode 
    permet de filtrer les lignes de données générées pour s'assurer qu'elles respectent les règles définies par l'utilisateur.
    """
    def check_condition(self,data):
        if self.conditions_data is None:
            return False
        
        for key,value in data.items():
            filtered_df = self.conditions_data[self.conditions_data['field'].str.contains(key)]
           
            if not filtered_df.empty  :
                for _, row in filtered_df.iterrows():
                    result=0
                    if self.operation(value,row['field']) :
                            list_conditions = row['conditions'].split("#")
                            
                            for condition in list_conditions:
                                
                                if not self.operation(data[condition.split(":")[0]],condition) :
                                    break
                                else:
                                    result+=1
                            if result == len(list_conditions):
                                return True

        return False
    
    
    """
    Cette méthode permet de réaliser différentes opérations de comparaison telles que l'égalité, la supériorité, l'infériorité,
    l'inclusion dans un intervalle, etc. Elle renvoie True si la comparaison est vérifiée, sinon elle renvoie False. Cette 
    fonction est utilisée dans la méthode check_condition pour vérifier si une ligne de données satisfait une condition donnée.
    """
    def operation(self,value,condition):
        
        
        operation = condition.split(':')[1]
        value2 = condition.split(':')[2]
        # Match case statement
        #print("hahahaahhahaha condition",condition)
        
            
        if(operation== "equal"):   
            result = value == value2
            return result
        if(operation== "sup"):
            result = float(value) > float(value2)
            return result
        if(operation== "inf"):
            result = float(value) < float(value2)
            return result
        if(operation== "include"):
            v1,v2=value2.split("_")
            result = (float(value) >= float(v1) and float(value)<= float(v2))
            return result

        if(operation=="sup and equal"):
            result = float(value) >= float(value2)
            return result
        if(operation== "inf and equal"):
            result = float(value) <= float(value2)
            return result
        if(operation== "not equal" ):
            result = value != value2
            return result

        

        
        """
        Cette méthode est responsable de la gestion des conditions basées sur des pourcentages pour une variable spécifique 
        (field)
        
        """
    def PercentageCondition(self ,field ,value ,DF , cpFields, dataNum): 
#         if(self.PercentageCondition(obj,attribut,donnees_generees,FieldsCp,n)):
        BackUpDf=pd.DataFrame(DF)
        if BackUpDf.empty :
            return True
        
            
        for key1 , value1 in field.percentage.items() :
            if '_' not in key1 and key1 == value :
                if((BackUpDf[field.name]==value).sum() >= int(value1*dataNum/100)):
                    (cpFields[cpFields.index(field)].percentage).pop(key1)
                    return False

            elif '_' in key1 :
                v1,v2=key1.split('_')
                if float(v1)<= float(value) <= float(v2) :

                    if((BackUpDf[field.name].between(v1,v2)).sum() >= int(value1*dataNum/100)):
                        (cpFields[cpFields.index(field)].percentage).pop(key1)
                        
                        return False
                           

        return True
    
    
    """
    Cette méthode génère les données en itérant jusqu'à ce que le nombre spécifié n soit atteint. La méthode itère jusqu'à ce que
    le nombre total de données soit atteint. Si un nom de fichier est fourni, elle appelle la méthode generate_random_data pour 
    générer les données en blocs de 1000 et les stocker dans le fichier. Elle met à jour l'itération après chaque bloc généré et 
    affiche un message pour indiquer la progression. Si aucun nom de fichier n'est fourni, elle retourne directement les données 
    générées. Cette méthode offre une flexibilité en permettant à l'utilisateur de choisir de stocker les données dans un fichier 
    ou de les récupérer directement selon ses besoins.
    """
    
    def generate(self, n ,filename=None):
        iteration=0
        while n>iteration:
            if(filename) :
                self.generate_random_data(1000,filename)
                iteration=iteration+1000
           
                print(f"Done Generating {1000} DATA")
            else :
                return self.generate_random_data(n)
                         
            
            
    """
    Cette méthode prend un objet Field (représentant une colonne) en entrée. Elle choisit aléatoirement un paramètre (valeur) de 
    l'objet Field et renvoie cette valeur choisie. L'objectif de cette méthode est de sélectionner aléatoirement une valeur à 
    partir de l'ensemble des valeurs disponibles dans l'objet Field, permettant ainsi de générer des données de manière aléatoire 
    tout en respectant la distribution des valeurs spécifiée par l'utilisateur.
    """
    def SplitInterval(self,obj):
        
        attribut = random.choices(list(obj.percentage.keys()))[0]

        if '_' in attribut:
            interval_start, interval_end = attribut.split('_')
            if '.' in attribut:
                if '.' not in interval_start:
                    nk = len(interval_end.split('.')[1])
                elif '.' not in interval_end :
                     nk = len(interval_start.split('.')[1])
                elif '.' in interval_start and '.' in interval_end :
                    nk = max(len(interval_start.split('.')[1]),len(interval_end.split('.')[1]))

                attribut = random.uniform(float(interval_start), float(interval_end))
                attribut = round(attribut * 10**nk) / 10**nk
            else : 
                attribut = random.randint(int(interval_start), int(interval_end))
        return attribut
                    
        
     

        

        
        
        
        
        
    