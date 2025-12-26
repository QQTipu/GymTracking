import pandas as pd
import streamlit as st
from datetime import datetime, timedelta

def get_program_day(date, start_date_str, skipped_days):
    """
    Calcule le jour du programme en fonction de la date de début
    et des jours skippés. Le jour est absolu (pas de cycle).
    """
    start = datetime.strptime(start_date_str, "%Y-%m-%d").date()
    
    # Gérer les différents types de date (datetime, date, string)
    if isinstance(date, str):
        current = datetime.strptime(date, "%Y-%m-%d").date()
    elif isinstance(date, datetime):
        current = date.date()
    else:
        current = date
    
    if current < start:
        return 1
    
    days_elapsed = (current - start).days
    
    skipped_before = len([d for d in skipped_days if d < str(current)])
    effective_days = days_elapsed - skipped_before
    
    program_day = effective_days + 1
    
    return program_day

def get_next_scheduled_day(start_date_str, skipped_days):
    """Retourne la date et le jour du programme pour demain"""
    tomorrow = (datetime.now() + timedelta(days=1)).date()
    next_day = get_program_day(tomorrow, start_date_str, skipped_days)
    return tomorrow, next_day

def get_exercise_stats(exercise_name, history, df_programme, program_length, current_date_str):
    """
    Calcule la charge maximale de la dernière séance et la charge maximale all-time
    pour un exercice donné, pour les séances antérieures à une date donnée.
    """
    exercise_history = []
    
    for date_str, session in sorted(history.items()):
        if date_str >= current_date_str:
            continue

        weights = session.get('weights', {})
        if not weights:
            continue
            
        day_number = session['day_number']
        day_in_cycle = (day_number - 1) % program_length + 1
        day_workout_df = df_programme[df_programme['Jour'] == day_in_cycle]
        
        exercise_rows = day_workout_df[day_workout_df['Exercice'] == exercise_name]
        
        # Recherche par nom d'exercice (plus robuste que l'index)
        session_weights = []
        for key, weight in weights.items():
            parts = key.split('_')
            if len(parts) >= 3:
                # Reconstruire le nom (au cas où il contient des underscores)
                stored_name = "_".join(parts[1:-1])
                if stored_name == exercise_name and weight > 0:
                    session_weights.append(weight)
        
        if session_weights:
            exercise_history.append({
                'date': date_str,
                'max_weight': max(session_weights)
            })

    if not exercise_history:
        return None, None

    last_max = exercise_history[-1]['max_weight']
    all_time_max = max(item['max_weight'] for item in exercise_history)
    
    return last_max, all_time_max