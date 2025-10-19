#!/usr/bin/env python3
"""
Script simple para añadir la columna titulo_adaptado
Se puede ejecutar con: python migrate_titulo_adaptado.py
"""
import os
from sqlalchemy import create_engine, text

def main():
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        print("❌ ERROR: DATABASE_URL no está configurada")
        return 1
    
    print("🔄 Conectando a la base de datos...")
    engine = create_engine(database_url)
    
    try:
        with engine.connect() as conn:
            print("✅ Conectado exitosamente")
            
            # Verificar si la columna ya existe
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='licitaciones' AND column_name='titulo_adaptado'
            """))
            
            if result.fetchone() is None:
                print("📝 Añadiendo columna titulo_adaptado...")
                conn.execute(text("ALTER TABLE licitaciones ADD COLUMN titulo_adaptado TEXT"))
                conn.commit()
                print("✅ Columna 'titulo_adaptado' añadida exitosamente")
            else:
                print("ℹ️  Columna 'titulo_adaptado' ya existe")
            
            print("✅ Migración completada")
            return 0
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return 1

if __name__ == "__main__":
    exit(main())

