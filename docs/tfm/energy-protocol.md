# Protocolo futuro de batería

No se han inventado consumos. Para comparar manual, continuo e inteligente se
usará el mismo dispositivo, batería inicial y duración fija, brillo y red iguales,
sin otras aplicaciones activas. Se registrarán `dumpsys batterystats` antes/después
y, si está disponible, un trace Perfetto. Cada escenario se repetirá en condiciones
documentadas; se conservará el intervalo completo y no se eliminarán outliers sin
criterio previo. Se anotarán temperatura, versión Android, pantalla visible y si el
servicio foreground seguía activo.
