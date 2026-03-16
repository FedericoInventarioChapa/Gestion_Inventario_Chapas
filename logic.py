import datetime
import pandas as pd

class SheetInventory:
    def __init__(self, sheet_name, full_sheet_length=13.0):
        self.sheet_name = sheet_name
        self.full_sheet_length = full_sheet_length
        self.full_sheets_count = 0
        self.cuts = [] 
        self.min_cut_length_to_save = 1.5 

    def add_full_sheets(self, quantity):
        """Añade chapas completas al inventario."""
        if quantity > 0:
            self.full_sheets_count += quantity
            return f"Se añadieron {quantity} unidades de {self.sheet_name}."
        return "La cantidad debe ser positiva."

    def take_material(self, length_needed, num_cuts=1):
        """
        Lógica unificada para tomar material. 
        Retorna (bool_éxito, mensaje_detalle, lista_de_registros)
        """
        successful_cuts = 0
        current_records = []
        
        for i in range(num_cuts):
            record = {
                'timestamp': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'sheet_type': self.sheet_name,
                'length_requested': length_needed,
                'success': False
            }

            # 1. Intentar con recortes
            suitable_cuts = [c for c in self.cuts if c >= length_needed]
            if suitable_cuts:
                selected_cut = min(suitable_cuts)
                self.cuts.remove(selected_cut)
                remnant = round(selected_cut - length_needed, 2)
                
                if remnant >= self.min_cut_length_to_save:
                    self.cuts.append(remnant)
                
                record.update({'source': 'Recorte', 'remnant': remnant, 'success': True})
                successful_cuts += 1
            
            # 2. Intentar con chapa completa
            elif self.full_sheets_count > 0:
                self.full_sheets_count -= 1
                remnant = round(self.full_sheet_length - length_needed, 2)
                
                if remnant >= self.min_cut_length_to_save:
                    self.cuts.append(remnant)
                
                record.update({'source': 'Chapa Completa', 'remnant': remnant, 'success': True})
                successful_cuts += 1
            else:
                break # No hay más material
            
            current_records.append(record)

        return (successful_cuts == num_cuts), current_records