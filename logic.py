import datetime

class SheetInventory:
    def undo_cut(self, source, length_requested, remnant):
        """Devuelve el material al inventario según de dónde se sacó."""
        # Si salió de un recorte, el recorte original era (pedido + lo que sobró)
        if source == 'Recorte':
            # Primero quitamos el sobrante que se había guardado (si es que se guardó)
            if remnant >= self.min_cut_length_to_save:
                if remnant in self.cuts:
                    self.cuts.remove(remnant)
            # Devolvemos el recorte original a la lista
            original_cut = round(length_requested + remnant, 2)
            self.cuts.append(original_cut)
            
        # Si salió de una chapa completa, simplemente la sumamos de nuevo
        elif source == 'Chapa Completa':
            # Quitamos el sobrante que generó de la lista de recortes
            if remnant >= self.min_cut_length_to_save:
                if remnant in self.cuts:
                    self.cuts.remove(remnant)
            self.full_sheets_count += 1
        return True
    def __init__(self, sheet_name, full_sheet_length=13.0):
        self.sheet_name = sheet_name
        self.full_sheet_length = full_sheet_length
        self.full_sheets_count = 0
        self.cuts = [] 
        self.min_cut_length_to_save = 1.50 

    def add_full_sheets(self, quantity):
        if quantity > 0:
            self.full_sheets_count += quantity
            return f"Se añadieron {quantity} unidades."
        return "Cantidad no válida."

    def take_material(self, length_needed, num_cuts=1):
        # REGLA: No cortes de 12m o más
        if length_needed >= 12.0:
            return False, [{"error": "Corte bloqueado: El largo debe ser menor a 12m."}]

        successful_cuts = 0
        current_records = []
        
        for i in range(num_cuts):
            record = {
                'timestamp': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'sheet_type': self.sheet_name,
                'length_requested': length_needed,
                'source': '',
                'remnant': 0,
                'success': False
            }

            # 1. Buscar en recortes
            suitable_cuts = [c for c in self.cuts if c >= length_needed]
            if suitable_cuts:
                selected_cut = min(suitable_cuts)
                self.cuts.remove(selected_cut)
                remnant = round(selected_cut - length_needed, 2)
                
                if remnant >= self.min_cut_length_to_save:
                    self.cuts.append(remnant)
                
                record.update({'source': 'Recorte', 'remnant': remnant, 'success': True})
                successful_cuts += 1
            
            # 2. Buscar en chapas completas
            elif self.full_sheets_count > 0:
                self.full_sheets_count -= 1
                remnant = round(self.full_sheet_length - length_needed, 2)
                
                if remnant >= self.min_cut_length_to_save:
                    self.cuts.append(remnant)
                
                record.update({'source': 'Chapa Completa', 'remnant': remnant, 'success': True})
                successful_cuts += 1
            else:
                break 
            
            current_records.append(record)

        return (successful_cuts == num_cuts), current_records
