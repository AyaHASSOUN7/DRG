import random
from constraint import Problem, ExactSumConstraint

# exceptions 
class DataFormatError(ValueError): 
    """Exception levée pour des erreurs de formatage des données (ex: ':' manquant)."""
    pass

class DataTypeError(ValueError): 
    """Exception levée quand un type de donnée est incorrect (ex: 'abc' au lieu d'un nombre)."""
    pass

class IntervalLogicError(ValueError): 
    """Exception levée pour un problème logique dans un intervalle (ex: début >= fin)."""
    pass

class VerificationPourcentageError(ValueError): 
    """Exception levée pour des erreurs de vérification de pourcentage."""
    pass

class key_Error(ValueError): pass
class IntervalOverlapError(ValueError): pass









# --- FONCTIONS UTILITAIRES ---
def parse_condition(condition_str):
    try:
        field, op, value = condition_str.strip().strip('()').split(':', 2)
        return {'field': field.strip(), 'op': op.strip(), 'value': value.strip()}
    except ValueError:
        raise ValueError(f"Format de condition invalide : '{condition_str}'")

def _check_value_satisfies_condition(key_to_check, op, condition_value_str):
    key_str = str(key_to_check)
    if op == "equal": return key_str == condition_value_str
    if op == "not equal": return key_str != condition_value_str
    try:
        if op == 'include':
            v1_str, v2_str = condition_value_str.split('_')
            return float(v1_str) <= float(key_str) <= float(v2_str)
        condition_value_float = float(condition_value_str)
        key_value_float = float(key_str)
        if op == 'sup': return key_value_float > condition_value_float
        if op == 'inf': return key_value_float < condition_value_float
        if op == 'sup and equal': return key_value_float >= condition_value_float
        if op == 'inf and equal': return key_value_float <= condition_value_float
    except (ValueError, IndexError):
        return False
    return False


class SmartPercentageDict:
    """ cette classe va envoyer les valeurs autorisées en fonction des règles de contraintes. """
    def __init__(self, field_name): self._field_name = field_name; self._base_percentages = {}; self._constraints = []; self._all_fields_distributions = {}; self.current_context = {}; self._temporarily_forbidden = set()

    def set_base_distribution(self, base_dict): self._base_percentages = base_dict

    def link_global_context(self, constraints, all_fields_distributions): self._constraints = constraints; self._all_fields_distributions = all_fields_distributions

    def get_allowed_values(self):
        all_values = list(self._base_percentages.keys())

        # AVANT TOUTE CHOSE, on enlève ce qui est sur la liste noire.
        allowed_by_percentage = {v for v in all_values if v not in self._temporarily_forbidden}

        if not self._constraints or not self.current_context: return all_values
        forbidden_values = set()
        for rule in self._constraints:
            if_cond, not_cond = rule['if'], rule['then_not']
            if not_cond['field'] == self._field_name and if_cond['field'] in self.current_context:
                valeur_generee = self.current_context[if_cond['field']]
                if _check_value_satisfies_condition(valeur_generee, if_cond['op'], if_cond['value']):
                    for val in all_values:
                        if _check_value_satisfies_condition(val, not_cond['op'], not_cond['value']):
                            forbidden_values.add(val)
        return [v for v in allowed_by_percentage if v not in forbidden_values]
    

    def keys(self): return self.get_allowed_values()

    def __iter__(self): return iter(self.keys())

    def __len__(self): return len(self.keys())

    def pop(self, key, default=None):
        # Au lieu de supprimer, on AJOUTE la clé à la liste noire.
        self._temporarily_forbidden.add(key)
        # On retourne la valeur, comme le ferait un vrai .pop()
        return self._base_percentages.get(key, default)
    
    # On lui apprend à OUBLIER la liste noire
    def reset_for_new_line(self):
        # On vide la liste noire pour repartir à zéro.
        self._temporarily_forbidden.clear()

    def items(self):
        allowed = self.get_allowed_values()
        return {k: v for k, v in self._base_percentages.items() if k in allowed}.items()
    
    def values(self):
        allowed = self.get_allowed_values()
        return {k: v for k, v in self._base_percentages.items() if k in allowed}.values()
    
    def __contains__(self, key): return key in self.get_allowed_values()

    def __getitem__(self, key):
        if key in self._base_percentages and key in self.get_allowed_values(): return self._base_percentages[key]
        raise KeyError(f"La clé '{key}' n'est pas autorisée dans le contexte actuel ou n'existe pas.")




# classe Field 
class Field:
    def __init__(self, name):
        self.name = name
        self.percentage = SmartPercentageDict(name)
        self._base_percentage_dist = {}

    def fill_map(self, data_list):
        """Analyse les données, valide la syntaxe et calcule une distribution de base valide."""
        valeurs_fixes = {}
        intervalles = {}
        cles_intervalle = [] 
        
        # partie syntaxe 

        for i, data_item in enumerate(data_list):
            if ':' not in data_item: 
                raise DataFormatError(f"Erreur à la ligne {i+1} ('{data_item}'): Le séparateur ':' est manquant.")
            parts = data_item.split(':', 1)
            key, value_str = parts[0], parts[1]

            if not key: 
                raise DataFormatError(f"Erreur à la ligne {i+1} ('{data_item}'): La clé est manquante.")
            
            if not value_str: 
                raise DataFormatError(f"Erreur à la ligne {i+1} ('{data_item}'): La valeur est manquante.")
            


            # pour la clé-intervalle
            if '_' in key:
                try:
                    interval_parts = key.split('_')
                    if len(interval_parts) != 2: raise DataFormatError(f"Ligne {i+1}: Format de clé-intervalle '{key}' invalide.")
                    start, end = float(interval_parts[0]), float(interval_parts[1])
                    if start >= end: raise IntervalLogicError(f"Ligne {i+1}: Dans la clé '{key}', le début doit être inférieur à la fin.")
                    cles_intervalle.append((start, end))
                except ValueError:
                    raise DataTypeError(f"Ligne {i+1}: Les bornes de la clé-intervalle '{key}' doivent être des nombres.")
        
            # vérification de la valeur-pourcentage
            if '_' in value_str:
                parts = value_str.split('_')
                if len(parts) != 2: raise DataFormatError(f"Ligne {i+1}: Format de valeur-intervalle invalide: 'start_end'")
                try:
                    start, end = float(parts[0]), float(parts[1])
                except ValueError:
                    raise DataTypeError(f"Ligne {i+1}: Les bornes de l'intervalle de pourcentage doivent être des nombres.")
                
                if start < 0 or end < 0: 
                    raise IntervalLogicError(f"Ligne {i+1}: Les pourcentages ne peuvent être négatifs.")
                
                if start >= end: 
                    raise IntervalLogicError(f"Ligne {i+1}: Début ({start}) doit être inférieur à la fin ({end}).")
                
                intervalles[key] = {'start': start, 'end': end}
            else:
                try:
                    value = float(value_str)
                except ValueError:
                    raise DataTypeError(f"Erreur à la ligne {i+1} ('{data_item}'): La valeur '{value_str}' n'est pas un nombre valide.")
                
                if value < 0: 
                    raise IntervalLogicError(f"Erreur à la ligne {i+1} ('{data_item}'): Un pourcentage ne peut pas être négatif.")
                valeurs_fixes[key] = value

        
        somme_des_fixes_check = sum(valeurs_fixes.values())
        somme_des_starts_check = sum(item['start'] for item in intervalles.values())
        somme_des_ends_check = sum(item['end'] for item in intervalles.values())

        somme_min_possible = somme_des_fixes_check + somme_des_starts_check
        somme_max_possible = somme_des_fixes_check + somme_des_ends_check

        print(f"\nAnalyse de l'ensemble des données pour le champ '{self.name}':")
        print(f"  - Somme des pourcentages fixes: {somme_des_fixes_check:.2f}%")
        print(f"  - Somme minimale possible (avec bornes 'start'): {somme_min_possible:.2f}%")
        print(f"  - Somme maximale possible (avec bornes 'end'): {somme_max_possible:.2f}%")

        if somme_max_possible < 100:
            raise VerificationPourcentageError(f"Erreur pour le champ '{self.name}': La somme maximale possible {somme_max_possible:.2f}% est inférieure à 100%.")
        
        if somme_min_possible > 100:
            raise VerificationPourcentageError(f"Erreur pour le champ '{self.name}': La somme minimale possible {somme_min_possible:.2f}% dépasse 100%.")
        
        print(f"  - Les pourcentages semblent cohérents, lancement de la vérification exacte...")



        # verification du chevauchement des intervalles

        if cles_intervalle:
            cles_intervalle.sort(key=lambda x: x[0])
            for i in range(len(cles_intervalle) - 1):
                if cles_intervalle[i][1] >= cles_intervalle[i + 1][0]:
                    raise IntervalOverlapError(f"Chevauchement de clés détecté pour le champ '{self.name}' entre {cles_intervalle[i]} et {cles_intervalle[i+1]}.")
            print(f"  - Aucune clé-intervalle ne se chevauche pour le champ '{self.name}'.")
       
       




        
        self._solve_and_populate_base_distribution(valeurs_fixes, intervalles)
        self.percentage.set_base_distribution(self._base_percentage_dist)
    
    def _solve_and_populate_base_distribution(self, valeurs_fixes, intervalles):
        
        somme_fixes = sum(valeurs_fixes.values())
        if not intervalles:
            if round(somme_fixes, 2) != 100.00: 
                raise VerificationPourcentageError(f"Pour le champ '{self.name}', la somme des pourcentages fixes est {somme_fixes}%, mais devrait être 100%.")
            self._base_percentage_dist = valeurs_fixes
            return
        
        problem = Problem()
        precision_multiplier = 100
        for key, interval in intervalles.items():
            start = int(interval['start'] * precision_multiplier); end = int(interval['end'] * precision_multiplier)
            problem.addVariable(key, range(start, end + 1))

        cible = 100.0 - somme_fixes
        cible_scaled = int(round(cible * precision_multiplier))
        problem.addConstraint(ExactSumConstraint(cible_scaled), list(intervalles.keys()))
        solution = problem.getSolution()

        if not solution: 
            raise VerificationPourcentageError(f"Vérification exacte ECHOUEE pour le champ '{self.name}'. Aucune combinaison ne peut sommer à 100%.")
        
        solution_float = {key: value / precision_multiplier for key, value in solution.items()}
        self._base_percentage_dist = {**valeurs_fixes, **solution_float}
        total = sum(self._base_percentage_dist.values())
        if abs(total - 100.0) > 1e-9:
             last_key = list(self._base_percentage_dist.keys())[-1]
             self._base_percentage_dist[last_key] += 100.0 - total
        print(f"  - Vérification exacte REUSSIE pour le champ '{self.name}'.")

    def link_global_context_to_percentage_dict(self, constraints, all_fields_distributions):
        self.percentage.link_global_context(constraints, all_fields_distributions)

    def update_percentage_context(self, current_line_data):
        self.percentage.current_context = current_line_data

    def reset_context_for_new_line(self):
        self.percentage.reset_for_new_line()

   

# # testing 
# if __name__ == "__main__":
#     tests = {
#         "Test 'Somme Trop Basse'": ["fixe:20.5", "intervalle:10_30"],
#         "Test 'Somme Trop Haute'": ["fixe:80", "intervalle:30_50"],
#         "Test 'Ensemble Valide'": ["fixe:30", "autre-fixe:10", "intervalle-A:20_40", "intervalle-B:10_30"],
#         "Test 'Erreur de Format Interne'": ["fixe:50", "TypeInvalide:abc", "intervalle:10_20"],
#         "test 'Erreur d'inclusion dans un intervalle des keys'": ["0_30:50", "25_80:20", "81_100:30"],
#         "Test 'Ensemble Valide'": ["fixe:30", "autre-fixe:10", "intervalle-A:20_40", "intervalle-B:10_30"],
#     }
#     for nom_test, jeu_de_donnees in tests.items():
#         print(f"\n======================\nLANCEMENT DU TEST : {nom_test}\n======================")
#         print("Données en entrée :", jeu_de_donnees)
#         try:
#             champ = Field("Testeur Final")
#             champ.fill_map(jeu_de_donnees)
#         except (VerificationPourcentageError, DataFormatError, DataTypeError, IntervalLogicError) as e:
#             print(f"\n  ❌ ERREUR CAPTURÉE : {e.__class__.__name__}")
#             print(f"     Message : {e}")









