from utils.cedula_extractor import clasificar_pago, extraer_cedulas


def test_extraer_cedula_simple():
    assert extraer_cedulas("PAGO V6919271 CUOTA") == ["V6919271"]


def test_extraer_cedula_con_guion():
    assert extraer_cedulas("TRF V-6919271") == ["V6919271"]


def test_extraer_cedula_juridica():
    assert extraer_cedulas("DEP J051151689") == ["J051151689"]


def test_extraer_multiples_cedulas():
    resultado = extraer_cedulas("V6919271 Y V4042020")
    assert "V6919271" in resultado
    assert "V4042020" in resultado


def test_sin_cedula():
    assert extraer_cedulas("COMISION BANCARIA") == []


def test_clasificar_pago_total():
    assert clasificar_pago(10000, 10000) == "total"


def test_clasificar_pago_parcial():
    assert clasificar_pago(5000, 10000) == "parcial"


def test_clasificar_pago_extraordinario():
    assert clasificar_pago(15000, 10000) == "extraordinario"


def test_clasificar_tolerancia():
    assert clasificar_pago(9950, 10000) == "total"
