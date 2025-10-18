"""
Script de prueba para el servicio de IA
"""
import sys
import os

# Agregar el directorio app al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from services.ai_service import AIService
import json


def test_stack_tecnologico():
    """Prueba la identificación de stack tecnológico"""
    print("\n" + "="*80)
    print("TEST 1: Identificación de Stack Tecnológico")
    print("="*80)
    
    ai = AIService()
    
    titulo = "Suministro de un sistema de protección para el correo electrónico de las Cortes de Aragón"
    descripcion = """Suministro e implementación de una solución de seguridad para correo electrónico 
    que incluya protección contra spam, phishing, malware y ransomware. La solución debe integrarse 
    con Microsoft Exchange y Office 365."""
    
    resultado = ai.identificar_stack_tecnologico(titulo, descripcion)
    
    if resultado:
        print("\n✅ Stack Tecnológico Identificado:")
        print(json.dumps(resultado, indent=2, ensure_ascii=False))
    else:
        print("\n❌ Error identificando stack tecnológico")


def test_conceptos_tic():
    """Prueba la clasificación por conceptos TIC"""
    print("\n" + "="*80)
    print("TEST 2: Clasificación por Conceptos TIC")
    print("="*80)
    
    ai = AIService()
    
    titulo = "Servicio de soporte técnico y actualización de sistema Plataforma de Administración Electrónica"
    descripcion = """Mantenimiento evolutivo y correctivo de la plataforma de administración electrónica, 
    incluyendo desarrollo de nuevas funcionalidades, migración a cloud, y soporte técnico 24/7."""
    
    resultado = ai.clasificar_conceptos_tic(titulo, descripcion)
    
    if resultado:
        print("\n✅ Conceptos TIC Identificados:")
        for concepto in resultado:
            print(f"  - {concepto}")
    else:
        print("\n❌ Error clasificando conceptos TIC")


def test_resumen_tecnico():
    """Prueba la generación de resumen técnico"""
    print("\n" + "="*80)
    print("TEST 3: Generación de Resumen Técnico")
    print("="*80)
    
    ai = AIService()
    
    titulo = "Desarrollo de aplicación móvil para gestión de expedientes administrativos"
    descripcion = """Desarrollo de una aplicación móvil nativa para iOS y Android que permita 
    a los ciudadanos consultar y gestionar sus expedientes administrativos. Debe incluir 
    autenticación con certificado digital, firma electrónica, y sincronización offline."""
    
    resultado = ai.generar_resumen_tecnico(titulo, descripcion)
    
    if resultado:
        print("\n✅ Resumen Técnico Generado:")
        print(json.dumps(resultado, indent=2, ensure_ascii=False))
    else:
        print("\n❌ Error generando resumen técnico")


def test_analisis_completo():
    """Prueba el análisis completo de una licitación"""
    print("\n" + "="*80)
    print("TEST 4: Análisis Completo de Licitación")
    print("="*80)
    
    ai = AIService()
    
    titulo = "Migración de infraestructura on-premise a cloud AWS con arquitectura de microservicios"
    descripcion = """Migración completa de la infraestructura actual (servidores físicos) a AWS, 
    implementando una arquitectura de microservicios con Docker y Kubernetes. Incluye migración 
    de bases de datos PostgreSQL a RDS, implementación de CI/CD con GitLab, monitorización con 
    Prometheus y Grafana, y formación del equipo técnico."""
    
    resultado = ai.analizar_licitacion_completa(titulo, descripcion)
    
    if resultado:
        print("\n✅ Análisis Completo:")
        print(json.dumps(resultado, indent=2, ensure_ascii=False))
    else:
        print("\n❌ Error en análisis completo")


if __name__ == '__main__':
    print("\n" + "="*80)
    print("PRUEBAS DEL SERVICIO DE IA - LITICIA")
    print("="*80)
    
    # Nota: Estas pruebas requieren una API key de OpenAI válida
    print("\n⚠️  NOTA: Estas pruebas consumen créditos de OpenAI API")
    print("⚠️  Asegúrate de tener configurada la variable OPENAI_API_KEY")
    
    try:
        test_stack_tecnologico()
        test_conceptos_tic()
        test_resumen_tecnico()
        test_analisis_completo()
        
        print("\n" + "="*80)
        print("✅ TODAS LAS PRUEBAS COMPLETADAS")
        print("="*80 + "\n")
    
    except Exception as e:
        print(f"\n❌ ERROR EN LAS PRUEBAS: {e}\n")
        import traceback
        traceback.print_exc()

