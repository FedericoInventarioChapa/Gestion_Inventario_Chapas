def take_material(self, length_needed, num_cuts=1):
        if length_needed >= 12.0:
            return False, [{"error": "Corte bloqueado: El largo debe ser menor a 12m."}]
        
        successful_cuts = 0
        current_records = []
        
        for i in range(num_cuts):
            record = {'timestamp': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 'sheet_type': self.sheet_name, 'length_requested': length_needed, 'source': '', 'remnant': 0, 'success': False}
            
            # --- FILTRO INTELIGENTE ---
            # Solo buscamos recortes que:
            # 1. Sean lo suficientemente largos (c >= length_needed)
            # 2. AL CORTARLOS, el sobrante sea 0 (corte exacto) O sea >= 1.5m
            suitable_cuts = [
                c for c in self.cuts 
                if c >= length_needed and (round(c - length_needed, 2) == 0 or round(c - length_needed, 2) >= self.min_cut_length_to_save)
            ]
            
            if suitable_cuts:
                selected_cut = min(suitable_cuts)
                self.cuts.remove(selected_cut)
                remnant = round(selected_cut - length_needed, 2)
                
                if remnant > 0: # Si no fue corte exacto, ya sabemos que es >= 1.5 por el filtro
                    self.cuts.append(remnant)
                
                record.update({'source': 'Recorte', 'remnant': remnant, 'success': True})
                successful_cuts += 1
                
            elif self.full_sheets_count > 0:
                # Aquí también validamos la chapa de 13m
                remnant = round(self.full_sheet_length - length_needed, 2)
                
                # Si de una chapa de 13m sobra menos de 1.5m (ej. corte de 12m)
                # pero como tu max_value es 11.9, esto siempre va a sobrar > 1.1m
                # Ajustamos para que cumpla tu regla de 1.5m
                if remnant < self.min_cut_length_to_save:
                     return False, [{"error": f"El corte de {length_needed}m dejaría un sobrante de {remnant}m (menor al mínimo de 1.5m)."}]

                self.full_sheets_count -= 1
                self.cuts.append(remnant)
                record.update({'source': 'Chapa Completa', 'remnant': remnant, 'success': True})
                successful_cuts += 1
            else:
                break 
            
            current_records.append(record)
            
        return (successful_cuts == num_cuts), current_records
