import datetime

class SheetInventory:
    def __init__(self, sheet_name, full_sheet_length=13.0):
        self.sheet_name = sheet_name
        self.full_sheet_length = full_sheet_length
        self.full_sheets_count = 0
        self.cuts = [] 
        self.min_cut_length_to_save = 1.50 

    def add_full_sheets(self, quantity):
        if quantity > 0:
            self.full_sheets_count += quantity
            return True
        return False

    def take_material(self, length_needed, num_cuts=1):
        """
        Procesa los cortes asegurando que nunca quede un sobrante < 1.5m.
        Si un recorte dejaría un resto pequeño, el sistema lo salta y busca una chapa nueva.
        """
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
            
            # FILTRO INTELIGENTE: 
            # 1. Que el recorte alcance (c >= length_needed)
            # 2. Que lo que sobre sea 0 (exacto) O sea >= 1.5m
            suitable_cuts = [
                c for c in self.cuts 
                if c >= length_needed and (round(c - length_needed, 2) == 0 or round(c - length_needed, 2) >= self.min_cut_length_to_save)
            ]
            
            if suitable_cuts:
                selected_cut = min(suitable_cuts)
                self.cuts.remove(selected_cut)
                remnant = round(selected_cut - length_needed, 2)
                
                if remnant > 0: 
                    self.cuts.append(remnant)
                
                record.update({'source': 'Recorte', 'remnant': remnant, 'success': True})
                successful_cuts += 1
                
            elif self.full_sheets_count > 0:
                # Validamos la chapa de 13m
                remnant = round(self.full_sheet_length - length_needed, 2)
                
                # Si de una chapa de 13m sobra menos de 1.5m, bloqueamos para evitar desperdicio
                if remnant < self.min_cut_length_to_save:
                     return False, [{"error": f"El corte de {length_needed}m dejaría un sobrante de {remnant}m (mínimo 1.5m)."}]

                self.full_sheets_count -= 1
                if remnant > 0:
                    self.cuts.append(remnant)
                
                record.update({'source': 'Chapa Completa', 'remnant': remnant, 'success': True})
                successful_cuts += 1
            else:
                # Si no hay recortes válidos ni chapas completas
                break 
            
            current_records.append(record)
            
        return (successful_cuts == num_cuts), current_records

    def undo_cut(self, source, length_requested, remnant):
        """
        Revierte un movimiento. Si el sobrante se guardó, lo quita. 
        Luego restaura la fuente original.
        """
        # Si el remanente es > 0, significa que se guardó en la lista 'cuts' (porque ya validamos que fuera >= 1.5)
        if remnant > 0 and remnant in self.cuts:
            self.cuts.remove(remnant)
        
        if source == 'Recorte':
            # Restauramos la pieza original que se usó
            original_piece = round(length_requested + remnant
