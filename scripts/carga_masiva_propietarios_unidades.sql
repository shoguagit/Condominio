-- =============================================================================
-- CARGA MASIVA REAL (data suministrada) — PROPIETARIOS + UNIDADES
-- Condominio destino: Condominio Las Mercedes de Paparo
-- =============================================================================
BEGIN;

DO $$
DECLARE
    v_condominio_id BIGINT;
BEGIN
    SELECT id INTO v_condominio_id
    FROM condominios
    WHERE nombre = 'Condominio Las Mercedes de Paparo'
    LIMIT 1;

    IF v_condominio_id IS NULL THEN
        RAISE EXCEPTION 'No existe el condominio: Condominio Las Mercedes de Paparo';
    END IF;

    WITH raw_text AS (
        SELECT $$NRO	NOMBRE Y APELLIDO	Cta	CORREO
A01	MARIANELLA OSSA	0,45	mossa53@gmail.com
A02	CARLOS EDUARDO ACUÑA PEREZ	0,45	ceacupez@gmail.com;fco_acu@hotmail.com
A03	JOSE PEREZ	0,45	damaris.perezv@gmail.com;josecheoperez2012@gmail.com
A04	JOSE PEREZ	0,45	damaris.perezv@gmail.com;josecheoperez2012@gmail.com
A05	ODALIS PAEZ	0,42	ODALISPAEZ@GMAIL.com
A06	ENRIQUE PINO Y CESAR VILLEGAS	0,33	cvillegass@hotmail.com
A07	GELPRIS MOTEMARANI	0,33	priscilapirona@hotmail.com;fco_acu@hotmail.com
A08	FRANCISCO JOSE ACUÑA PEREZ	0,42	fco_acu@homail.com;fco_acu@hotmail.com
A09	MIGNOLIA J COSTE	0,43	mignoliac06@gmail.com
A10	BELKIS ALVAREZ	0,33	pequita_25@hotmail.com
A11	Victor Viera / Gabriela Contreras	0,30	gabigovea14@gmail.com
A12	XIOMARA HERRERA	0,33	xherreral@gmail.com
A13	LORENA CARRILLO	0,43	locarrillom@gmail.com
B01	ROBERTO SPARACINO ROCCARO Y ANDREA MATILDE MENESES	0,45	robertosparacino @gmail.com
B02	SILVIA GUARIGUAN	0,45	gsilvia_marlene@hotmail.com;gsilvia_marlene@hotmail.com
B03	ROSELIN QUINTERO	0,45	roseliveraza@yahoo.es
B04	FRANCISCO LACORTE	0,45	pinshopregalos@hotmail.com
B05	VICTOR ALVAREZ	0,42	victorsalvarezg@hotmail.com
B06	PEDRO CENTENO	0,33	pedromanuelcenteno838@gmail.com
B07	HILDUBRANDO USECHE	0,33	dora_b_1989@hotmail.com
B08	LUISA LOW	0,42	meche1201@gmail.com
B09	JOSE ALEXANDER MORENO QUIÑONES	0,43	alexandermoreno601@gmail.com
B10	SR WILLIAM	0,33	tatianaandara@gmail.com
B11	ALFONZO GARCIA	0,30	ags1961@gmail.com
B12	NORMA MERCHAN	0,33	ranfi1212@hotmail.com;ireiba@hotmail.com
B13	YANIFER VALDEZ RIVERO	0,43	yaniferchris@gmail.com
C01	GLADYZ BERRIOS	0,45	guayana1961@gmail.com
C02	RAIZA NUÑEZ	0,45	pelucc@gmail.com;raizanuez@yahoo.es
C03	ANGELICA PALACIOS	0,45	angelicapalacios1108@gmail.com
C04	MARGARITA DE HERNANDEZ	0,45	vidriosmayjos@gmail.com;vidriosmay-jos@hotmail.com
C05	VICTOR ESCALONA PACHECO	0,42	
C06	JORGE SZEPLAKI	0,33	jszeplaki@gmail.com
C07	HUMBERTO MANRIQUE	0,33	hum060356@gmail.com
C08	JOSE A. GONZALEZ	0,42	mgsonocare@gmail.com
C09	ENRIQUE ACEVEDO RIVAS Y JANET MENA NUÑEZ	0,43	janeth.mena@hotmail.com
C10	MIGUEL ALBERTO BENTANCOURT	0,33	abuelitomiguel15@gmail.com
C11	JOSE BASTIDAS	0,30	jose.bastidas@bt.gob.ve
C12	GERMAN RODRIGUEZ	0,33	lindaabalo@gmail.com
C13	FRAINETT PAOLA ARIAS PULIDO	0,43	FRAINETT.ARIAS.SUCRE@GMAIL.COM
D01	BALTAZAR IZQUIERDO	0,45	diazjorge169@gmail,com;jfrecontreras@gmail.com
D02	CARLOS ROMERO	0,45	jonathanmarquez9@gmail.com;jonathanmarquez9@gmail.com
D03	FRANCISCO GOMEZ	0,45	zizabet@hotmail.com
D04	Ricardo Alberto Paredes hany	0,45	raparedesh@gmail.com
D05	SUSANA CHIN HUNG	0,42	
D06	GLADYS FERNANDEZ	0,33	katyuskaf@gmail.com;adelmof@gmail.com
D07	TURCSY SIMANCAS	0,33	analuisarodrigueztorralbo@gmail.com
D08	TURSCY SIMANCAS	0,42	ochoakarin74@gmail.com
D09	EVELYN PEREZ	0,61	evelinperezo@hotmail.com
D10	EGLENIS ZULAY SALDIVIA	0,71	cuentasxcobrar_antojitos@yahoo.es
D11	BRUNILDA TRINIDAD YEGUEZ ALCAZAR	0,64	Byeguez@e-bcorp.com
D12	ANGELICA MILAGROS RANGEL CORDOVA	0,61	angelica.rangel9@gmail.com
D13	RAFAEL JAIME	0,57	dilibetsy@gmail.com
E01	FLORINDA PEREIRA Y JOSE HERNANDEZ	0,45	florindapereira71@gmail.com
E02	MIRKA IANNACCI	0,45	mirkanelly@yahoo.com;mirkaiannacci@gmail.com
E03	FLOR QUINTERO	0,45	aurielrubi@hotmail.com
E04	CARLOS DANIEL GUANCHEZ QUINTERO	0,45	carlosguanchez@hotmail.com
E05	DANIEL ALEJANDRO MANZO	0,42	danielmanzo107@gmail.com
E06	ALEXANDER JOSE RODRIGUEZ ZABALA	0,33	ajrz061972ar@gmail.com;
E07	JOSE ATUNES y ISABEL ANTUNES	0,33	isabela04@gmail.com
E08	IGOR BETANCOURT	0,42	ibetan10@gmail.com
E09	OSCAR DANIEL PICALUA	0,61	oscardanielpicaluademarchi@gmail.com;oscardaniel.picalua@gmail.com
E10	RAUL VILAR	0,71	rauvi191060@hotmail.com
E11	ADOLFO NICOLOSO	0,64	nicolosofg@gmail.com;Amartinez@aluminionicoloso.com
E12	ARMANDO NUÑEZ	0,61	ajng49@gmail.com;alejandrocimarostivivas@yahoo.es
E13	CARMEN DE VALLE OROZCO Y ALEJANDRO CIMAR	0,57	orozcosala@hotmail.com;alejandrocimarostivivas@yahoo.es
F01	DAYANA AMERICA MORENO PEREZ	0,45	dayanamoreno1503@gmail.com
F02	MIGUEL ANGEL GARCIA	0,45	marciel.rodriguez@gmail.com;
F03	TOMAS LAREZ	0,45	LAREZADRIAN1809@GMAIL.com
F04	NANCY VILLAROEL	0,45	nancyvilla51@hotmail.com;nancyvillarroel51@gmail.com
F05	SAUL CABRERA	0,42	saul.cabrera@me.com;scabrera@consultores21.com
F06	PABLO CARDENAS	0,33	pablor.cardenas@gmail.com;rociocar218@hotmail.com
F07	SHEYLA DAYANA RIVAS	0,33	karinaice@gmail.com
F08	ROBERTO GABALDON	0,42	elidegabaldon@hotmail.com
F09	HASSAN SHARAM	0,61	oficinatrenzascarrizal@gmail.com
F10	JUAN LUIS PEREZ RAMOS	0,71	marcov.tixe@gmail.com;chrisaltami@gmail.com
F11	CARLOS RIVAS	0,64	crivas79@gmail.com
F12	EMILIS ELENA ABREU CASTILLO	0,61	pabloski1971@gmail.com
F13	EDDIE PERNALETTE	0,57	epernalette@gmail.com;epernalette@gmail.com
G01	ADELINA AYERBE DE SALAZAR y FREDDY SALAZAR	0,45	adelinaayerbe52@gmail.com;adelina.salazar@hidropet.com
G02	CESAR SALAZAR y JOSEFINA DE SALAZAR	0,45	josefinas1@hotmail.com
G03	CARLOS KROOP	0,45	carloskroop@gmail.com
G04	TATIANA R ANDARA G	0,45	tatianaandara@gmail.com
G05	JESUS DANIEL PRATO	0,42	yesdanp@gmail.com
G06	NELSON SANCHEZ	0,33	barriosangelica6@hotmail.com
G07	OSWALDO SALAZAR	0,33	josefinagsalazar@hotmail.com;oesm.mail@gmail.com
G08	JOSE LUIS ARGUELLES y ALEXIS ARGUELLES	0,42	arguelles.joseluis@gmail.com
G09	ROSA ARTIGAS / JOSE CONTRERAS	0,61	rosartigas@hotmail.com
G10	WILLIAM BAROS LUZANO	0,71	williambal@hotmail.com
G11	MARIA A BAGLIO	0,64	davidgarcia75@hotmail.com
G12	HECTOR LOPEZ	0,61	mariajosesraposo@gmail.com
G13	GUSMERY AREVALO	0,57	YOLEIDILOPEZ929@GMAIL.COM
H01	MANUEL VIEIRA DA SILVA	0,45	vierasoy@hotmail.com
H02	LEONOR HIDALGO DE HERRERA	0,45	leonorhidalgo20@gmail.com;leonorihidalgo@hotmail.com
H03	EDMUND RIVAS	0,45	edmondrivas@gmail.com
H04	ELIZABETH SALINAS	0,45	leonorhidalgo20@gmail.com;salinas.elizabeth61@gmail.com
H05	LUIS PELLA	0,42	joserafaelgonzaleza@gmail.com
H06	LOURDES DE MARZULLI	0,33	lmarzulli@hotmail.com
H07	ROSALIA RUOCCO	0,33	rosaliaruocco@yahoo.com
H08	JUAN CARLOS ACUÑA PEREZ	0,42	k_mastron@hotmail.com;fco_acu@hotmail.com
H09	ARIANNEE CAFARELLI	0,44	arianne.cg@gmail.com;arianne.cg@gimail.com
H10	FLORENCIO MORENO	0,72	flormoreca@hotmail.com
H11	JORGE EDUARDO OLIVERO MARQUEZ	0,30	jolivero13@gmail.com;jolivero13@gmail.com
H12	ROMULO GONZALEZ	0,72	romujoh@gmail.com;romujoh@gmail.com
H13	EFRAIN SANCHEZ CASTILLO	0,44	agevenempre2@hotmail.com;enger2312@hotmail.com
I01	ELIZABETH RAVELO HURTADO	0,45	maldonadooj@gmail.com
I02	ELIZABETH RAVELO y OMAR MALDONADO	0,45	maldonadooj@gmail.com
I03	JORGE PAREDES HANY	0,45	jorgehanypapa@gmail.com
I04	EDUARDO PLAZA	0,45	plazaedu@yahoo.es
I05	FRANCO CARBONI	0,42	jesuscarrero8@hotmail.com
I06	NELIDA ZAMBRANO y DULCE CHAPARRO	0,33	dulcechaparro@hotmail.com
I07	IVAN BASTIDAS	0,33	ivanbastidas68@hotmail.com
I08	ANA ANDREINA DARVWICH PEREZ	0,42	andreinadarwich@gmail.com
I09	LUIS A. DARWICH PEREZ	0,44	ludarwich@hotmail.com
I10	CATHERINE IBAÑEZ	0,72	catherineibanez09@gmail.com
I11	JORGE ROJAS y FELIPE PERALTA	0,30	jrojas.almagal@gmail.com
I12	JOSE MARTINEZ	0,72	aserraderoelsol@gmail.com
I13	IRENE DE CADENAS	0,44	marimicadenas@gmail.com;rcadenasch@yahoo.com
J01	CRISTERO PIMENTEL	0,45	ramonarmas2818@gmail.com
J02	ROSA DE DIMURO	0,45	unibaldimuro07@gmail.com
J03	LISBETH BOLIVAR	0,45	lisbettbq@gmail.com;lisbettbq@gmail.com
J04	MARITZA ANGARITA	0,45	maritzanga@gmail.com
J05	CARLOS RODRIGUEZ	0,42	carlaj.rodriguez@hotmail.com
J06	RAFAEL URIBE	0,33	ruribe49@hotmail.com;ruribe49@hotmail.com
J07	DANIEL FERREIRA CORREIA	0,33	danielfc78@gmail.com;danielfc78@hotmail.com
J08	PEDRO URBINA	0,42	marvicpermar@gmail.com
J09	FLOR DE MARIA ARREAZA MARRERO	0,44	tuttyarreaza@gmail.com;arreazaflor@hotmail.com
J10	CARLOS PEREZ	0,72	closingby@gmail.com;carlosfrenen@gmail.com
J11	HAYDEE BASTIDAS	0,30	jmoralesbastidas@hotmail.com
J12	ALBERTO OBENZA	0,72	graficastramalit@gmail.com
J13	BALBINA PEREZ	0,44	titorrero@gmail.com
K01	INDIRA FARIAS	0,45	ifarias@miccct.com;reiymata13@hotmail.com
K02	BLANCO BENITEZ LORENZA DE JESUS	0,45	luisraul46@hotmail.com
K03	NORKIS ZAMBRANO	0,45	norkiszambrano@gmail.com
K04	MARIA DEL CARMEN PEREIRA	0,45	florindapereira71@gmail.com
K05	BERNA SORZANO	0,42	durmienteber@hotmail.com;durmienteber@hotmail.com
K06	HERNAN GRAFEE y LISETTET GRAFEE	0,33	lisette_graffe@hotmail.com
K07	SONIA MARGARITA LLANES NIETO	0,33	llanessonia28@gmail.com
K08	REINA GONZALEZ y JUAN GONZALEZ	0,42	rgomez3838@gmail.com
K09	ABEL RODRIGUEZ ALFONSO	0,61	ebello_3@hotmail.com;abelrodr@gmail.com
K10	HECTOR DIAZ	0,71	hectordn@gmail.com
K11	NORA BUSTAMANTE DE ALAYETO y MANUEL ALAYET	0,64	mralayeto@hotmail.com;mralayeto@hotmail.com
K12	ERNESTO GIRONES	0,61	manufacturasgiron21ca@gmail.com;manufacturasgiron21ca@gmail.com
K13	RAFAEL PRATO	0,57	rp007_2006@yahoo.es;rp007_2006@yahoo.es
L01	RAMON ENRIQUE PLANAS	0,45	marisamattioli@hotmail.com
L02	EDGAR IRIARTE y MARICELA RODRIGUEZ	0,45	edgaririarte101@hotmail.com;mrodriguez@acorentacar.com
L03	SURKANIA	0,45	surkania@hotmail.com
L04	ALBERTO PAEZ	0,45	paezrollys@gmail.com
L05	IGNACIO SABINO	0,42	msousam05@gmail.com
L06	REINA TORO	0,33	idiaztoro@gmail.com;iraniblanco9@gmail.com
L07	ZULEIME SANCHEZ	0,33	zuleime123@gmail.com
L08	LUIGI BERSANY	0,42	bersany@hotmail.com
L09	GLADYS CARVALLO DE SANCHEZ	0,61	yalitagladyscarvallo@gmail.com
L10	JUAN AKINO	0,71	juanaquino8724@gmail.com
L11	OSWALDO MONTERO	0,64	snaidiordaz@gmail.com
L12	CARMEN AGUILERA PEREIRA	0,61	pereiranancy72@gmail.com;pereiranancy72@gmail.com
L13	ANTONIO FORGIONE	0,57	maria.cogliano@gmail.com;tallerlalagunita@hotmail.com
M01	KARINA ESTHER DIAZ	0,45	karinaice@gmail.com
M02	NELLY OMAÑA	0,45	nellymorela@gmail.com
M03	CARMEN ARVELO	0,45	arvelopez@hotmail.com;arvelopez@hotmail.com
M04	ZULAY MORALES	0,45	carlaj.rodriguez@hotmail.com
M05	JHOAN QUINTERO	0,42	johqui79@hotmail.com
M06	JOSE ALBERTO GARCIA	0,33	nsolorzano50@hotmail.com
M07	NORMA MORALES	0,33	normaana1944@gmail.com
M08	OLGA BORRERO	0,42	maitet48@gmail.com;maitet48@gmail.com
M09	CARLOS BOULTON	0,61	boultoncarlos@hotmail.com;aidalanda@hotmail.com
M10	EDGAR MANUEL MATERANO PERNIA	0,71	darinedarwich@hotmail.com
M11	MANUEL RIVERO	0,64	mariagabrielarojas@gmail.com;maria_vv13@hotmail.com
M12	GUSTAVO GONZALEZ	0,61	quadrogg@gmail.com;quadrogg@gmail.com
M13	LETICIA MARTINEZ DE DIAZ	0,57	compumad2@gmail.com
N01	TRINO DIAZ Y ESTHER DE DIAZ	0,45	karinaice@gmail.com
N02	ELIAS ELJURIS	0,45	bertaeljuri@me.com;saileef@gmail.com
N03	SILVERO PATO BARREIROS	0,45	silvepb61@gmail.com
N04	CARLOS TORRES	0,45	rosalalberto5@gmail.com;rosalalberto@hotmail.com
N05	MARYS T. DE PEREZ	0,42	extralicorbeach@gmail.com;
N06	LUIS MATA ROBLES Y BLANCA MIRALLES	0,33	luermaro@gmail.com
N07	MARIA CRISTINA GARCIA	0,33	mc427242@gmail.com
N08	INDALETO PEREIRA	0,42	florindapereira71@gmail.com
N09	IRAIMA CORDERO	0,61	corderoiraima@gmail.com
N10	YRAIDA CRISTINA RODRIGUEZ	0,71	iraida25@gmail.com
N11	LUIS RAMIREZ	0,64	evis1011@hotmail.com
N12	SINUER V POYER ROJAS	0,61	psinue02@gmail.com
N13	JOSE MANUEL LAMAS	0,57	hb.bravo1968@gmail.com
O01	CORINA RODRIGUEZ	0,45	corinarodriguez948@gmail.com
O02	JULIO CESAR MARTINEZ	0,45	Cedenomartinez@gmail.com
O03	ALBERTO VIEIRA y VERA VIEIRA	0,45	calumaro@gmail.com
O04	CIRA CARINA HEEGER ROMAN	0,45	heegerc@hotmail.com
O05	JESUS VERA	0,42	enjefe1966@gmail.com
O06	LUZ MARINA CAVANIER PEÑA	0,33	luzmcavanierp@gmail.com
O07	GIUSTINO D ANGELO	0,33	giustinodangelo@gmail.com
O08	ANA MIREYA MARTINEZ	0,42	anamireya23@hotmail.com
O09	LUIS ALBERTO DELGADO y GLORIA DELGADO	0,43	delgrosana@gmail.com
O10	JORGE BEZARA	0,33	jbezara@gmail.com
O11	FRANCISCO CONTRERAS	0,30	eleonorgarcia@hotmail.com
O12	CARLA RODRIGUEZ	0,33	carlaj.rodriguez@hotmail.com;carlaj.rodriguez@hotmail.com
O13	FREDDY HIDALGO	0,43	gabriel@venezuelaturistica.com;webmaster@venezuelaturistica.com
P01	JOSEPH DELUCAS	0,45	tecnico@labdai.com
P02	Gineth Arias	0,45	Gineth.arias.sucre@gmail.com
P03	CARMEN SALAÑO DE AVILA	0,45	alejandroavila70@gmail.com;carmensalano@Gmail.com
P04	CIPRIANO DUARTE	0,45	ciprianoduarte@hotmail.com
P05	GLORIA VELIZ	0,42	gloriaveliz27@gmail.com
P06	CARLOS ANTONIO CAMACHO	0,33	flintcamacho@outlook.com
P07	GRACIELA REBOLLEDO	0,33	gabolar82@hotmail.com
P08	JUAN DE ABREU FERREIRA	0,42	juandeabreu6923@gmail.com;juandeabreu94@hotmail.com
P09	NELIDA DE ACOSTA	0,43	silviacosta954@hotmail.com;nelidajuana82@hotmail.com
P10	NELIDA DE ACOSTA	0,33	silviacosta954@hotmail.com;nelidajuana82@hotmail.com
P11	TERESA DE ROYER	0,30	tbigott55@yahoo.com
P12	ZENITH FUENMAYOR y EDUARDO FUENMAYOR PULID	0,33	zenyth0902@hotmail.com
P13	LEONCIO RODRIGUEZ	0,43	lrod1209@gmail.com;
Q01	CARMEN SALAÑO DE AVILA	0,45	alejandroavila70@gmail.com;carmensalano@hotmail.com
Q02	FRANCISCO CONTRERAS Y ELEONOR GARCIA	0,45	eleonorgarcia@hotmail.com;eleonorgarcia@hotmail.com
Q03	EUSEBIO DOS SANTOS TEXEIRA	0,45	correiaagueda31@gmail.com
Q04	NATALIA ESTHER TUFFI	0,45	viajeront@gmail.com
Q05	PASCUALINA PAPA DE ROSI	0,42	gemmarossipapa@gmail.com
Q06	MIGUEL JIMENEZ (HIJO)	0,33	jimenez468@gmail.com
Q07	EDUARDO ABAD	0,33	chitty91@hotmail.com
Q08	ALEJANDRA LANDAETA	0,42	anais_alejandral@hotmail.com
Q09	YELITZA RAMOS- NELSON BOLIVAR	0,43	nelsonjosebolivarmartinez@gmail.com;yelitzaramosblanco@hotmail.com
Q10	REINA CEDEÑO	0,33	ebcedeno@yahoo.com;cedreina@yahoo.com
Q11	IBIS DE MARCELYS y ROXANA DELGADO	0,30	ibismdelgadoa@yahoo.com;ags1961@gmail.com
Q12	REINALDO MATA REYES	0,33	ifarias@miccct.com;reiymata13@hotmail.com
Q13	JOSE MANUEL HERNANDEZ y HILDA DE HERNANDE	0,43	marisaherno@gmail.com;mihn67@hotmail.com$$ AS txt
    ),
    lines AS (
        SELECT trim(linea) AS linea
        FROM raw_text,
        LATERAL regexp_split_to_table(txt, E'\n') AS linea
        WHERE trim(linea) <> ''
          AND trim(linea) !~* '^NRO\s+'
    ),
    parsed AS (
        SELECT
            split_part(linea, E'	', 1) AS nro,
            split_part(linea, E'	', 2) AS nombre_apellido,
            split_part(linea, E'	', 3) AS cta_raw,
            split_part(linea, E'	', 4) AS correo_raw
        FROM lines
    ),
    src AS (
        SELECT
            trim(nro) AS codigo_unidad,
            trim(nombre_apellido) AS nombre_propietario,
            NULL::TEXT AS cedula,
            NULL::TEXT AS telefono,
            NULLIF(
                regexp_replace(
                    regexp_replace(
                        regexp_replace(lower(trim(correo_raw)), '\s*@\s*', '@', 'g'),
                        '\s*;\s*', ';', 'g'
                    ),
                    ';+$', '', 'g'
                ),
                ''
            ) AS correo,
            'Apartamento'::TEXT AS tipo_unidad,
            'Propietario'::TEXT AS tipo_condomino,
            NULL::TEXT AS piso,
            COALESCE(NULLIF(replace(trim(cta_raw), ',', '.'), ''), '0')::NUMERIC(8,4) AS indiviso_pct,
            TRUE AS activo_unidad
        FROM parsed
        WHERE trim(nro) <> ''
    ),
    dedup_src AS (
        SELECT DISTINCT ON (codigo_unidad)
            *
        FROM src
        ORDER BY codigo_unidad
    ),
    ins_prop AS (
        INSERT INTO propietarios (condominio_id, nombre, cedula, telefono, correo, activo)
        SELECT
            v_condominio_id,
            s.nombre_propietario,
            s.cedula,
            s.telefono,
            s.correo,
            TRUE
        FROM dedup_src s
        WHERE NOT EXISTS (
            SELECT 1
            FROM propietarios p
            WHERE p.condominio_id = v_condominio_id
              AND (
                    (s.correo IS NOT NULL AND lower(p.correo) = s.correo)
                 OR (s.correo IS NULL AND upper(trim(p.nombre)) = upper(s.nombre_propietario))
              )
        )
        RETURNING id
    ),
    src_prop AS (
        SELECT
            s.*,
            (
                SELECT p.id
                FROM propietarios p
                WHERE p.condominio_id = v_condominio_id
                  AND (
                        (s.correo IS NOT NULL AND lower(p.correo) = s.correo)
                     OR (s.correo IS NULL AND upper(trim(p.nombre)) = upper(s.nombre_propietario))
                  )
                ORDER BY p.id
                LIMIT 1
            ) AS propietario_id
        FROM dedup_src s
    ),
    ins_uni AS (
        INSERT INTO unidades (
            condominio_id,
            codigo,
            numero,
            tipo,
            tipo_propiedad,
            indiviso_pct,
            estado_pago,
            propietario_id,
            alicuota_id,
            tipo_condomino,
            piso,
            activo,
            saldo
        )
        SELECT
            v_condominio_id,
            sp.codigo_unidad,
            sp.codigo_unidad,
            sp.tipo_unidad,
            sp.tipo_unidad,
            sp.indiviso_pct,
            'al_dia',
            sp.propietario_id,
            NULL,
            sp.tipo_condomino,
            sp.piso,
            sp.activo_unidad,
            0.00
        FROM src_prop sp
        WHERE sp.propietario_id IS NOT NULL
          AND NOT EXISTS (
              SELECT 1
              FROM unidades u
              WHERE u.condominio_id = v_condominio_id
                AND u.codigo = sp.codigo_unidad
          )
        RETURNING id
    ),
    src_full AS (
        SELECT
            sp.*,
            (
                SELECT u.id
                FROM unidades u
                WHERE u.condominio_id = v_condominio_id
                  AND u.codigo = sp.codigo_unidad
                LIMIT 1
            ) AS unidad_id
        FROM src_prop sp
    )
    INSERT INTO unidad_propietarios (unidad_id, propietario_id, activo, es_principal)
    SELECT sf.unidad_id, sf.propietario_id, TRUE, TRUE
    FROM src_full sf
    WHERE sf.unidad_id IS NOT NULL
      AND sf.propietario_id IS NOT NULL
      AND NOT EXISTS (
          SELECT 1
          FROM unidad_propietarios up
          WHERE up.unidad_id = sf.unidad_id
            AND up.propietario_id = sf.propietario_id
      );

    RAISE NOTICE 'Carga masiva completada para condominio_id=%', v_condominio_id;
END $$;

COMMIT;
