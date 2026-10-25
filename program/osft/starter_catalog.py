"""Food-truck starter catalog — products only, NO prices.

Every row: name | Spanish name | counting unit | units per case (blank = not sold by case) |
typical pack (descriptive only) | default storage zone.
Pack sizes are common US foodservice packs, offered as a starting point; check them
against your own vendor's spec sheets. Cost is always left blank for you to fill in.
"""

from __future__ import annotations

_RAW = """
## Proteins
Ground beef 80/20|Carne molida 80/20|lb|10|10 lb chub|cooler
Ground beef 85/15|Carne molida 85/15|lb|10|10 lb chub|cooler
Beef skirt steak|Arrachera de res|lb|20|~20 lb case|cooler
Beef flank steak|Falda de res|lb|20|~20 lb case|cooler
Beef chuck roll|Espaldilla de res|lb|60|~60 lb case|cooler
Beef brisket|Pecho de res (brisket)|lb|60|~60 lb case|cooler
Beef cheek (cachete)|Cachete de res|lb|20|~20 lb case|cooler
Beef tongue (lengua)|Lengua de res|lb|20|~20 lb case|cooler
Beef tripe|Tripa de res|lb|20|~20 lb case|cooler
Burger patties 4 oz|Hamburguesas 4 oz|ea|40|10 lb case (40 ct)|freezer
Burger patties 1/3 lb|Hamburguesas 1/3 lb|ea|30|10 lb case (30 ct)|freezer
Smash burger balls 3 oz|Bolitas para smash 3 oz|ea|53|10 lb case|cooler
Hot dogs all-beef|Salchichas de res|ea|80|10 lb case (8/1)|cooler
Bratwurst|Bratwurst|ea|48|10 lb case|freezer
Chorizo (Mexican, fresh)|Chorizo mexicano|lb|10|10 lb case|cooler
Chicken thigh boneless|Muslo de pollo sin hueso|lb|40|40 lb case|cooler
Chicken breast boneless|Pechuga de pollo sin hueso|lb|40|40 lb case|cooler
Chicken wings|Alitas de pollo|lb|40|40 lb case|freezer
Chicken tenders breaded|Tiras de pollo empanizadas|lb|10|2 x 5 lb bags|freezer
Chicken (whole)|Pollo entero|ea|12|12 ct case|cooler
Pork shoulder (butt)|Paleta de cerdo|lb|70|~70 lb case|cooler
Al pastor pork (marinated)|Carne al pastor|lb|10|10 lb pack|cooler
Carnitas (cooked, frozen)|Carnitas (congeladas)|lb|20|4 x 5 lb bags|freezer
Bacon sliced|Tocino rebanado|lb|15|15 lb case|cooler
Ham sliced|Jamon rebanado|lb|12|6 x 2 lb|cooler
Pulled pork (cooked)|Cerdo deshebrado|lb|10|2 x 5 lb|freezer
Pork belly|Panceta de cerdo|lb|20|~20 lb case|cooler
Shrimp 21/25 raw|Camaron 21/25 crudo|lb|10|5 x 2 lb bags|freezer
Shrimp 41/50 raw|Camaron 41/50 crudo|lb|10|5 x 2 lb bags|freezer
White fish fillet (cod/pollock)|Filete de pescado blanco|lb|10|10 lb case|freezer
Mahi mahi portions|Porciones de mahi mahi|lb|10|10 lb case|freezer
Fish sticks/strips battered|Tiras de pescado empanizadas|lb|10|10 lb case|freezer
Ground turkey|Pavo molido|lb|10|10 lb case|cooler
Lamb leg (boneless)|Pierna de cordero|lb|20|~20 lb case|cooler
Birria beef (goat/beef mix)|Carne para birria|lb|20|~20 lb case|cooler
Plant-based ground|Molida vegetal|lb|10|10 lb case|cooler
Plant-based patties|Hamburguesa vegetal|ea|40|40 ct case|freezer
Tofu extra firm|Tofu extra firme|ea|12|12 x 14 oz|cooler
Eggs large|Huevos grandes|ea|180|15 dozen case|cooler
Liquid eggs|Huevo liquido|qt|12|12 x 32 oz|cooler
## Dairy
Shredded cheese (Mexican blend)|Queso rallado (mezcla mexicana)|lb|20|4 x 5 lb bags|cooler
Shredded cheddar|Queso cheddar rallado|lb|20|4 x 5 lb bags|cooler
Shredded mozzarella|Queso mozzarella rallado|lb|20|4 x 5 lb bags|cooler
Monterey Jack shredded|Queso Monterey Jack rallado|lb|20|4 x 5 lb|cooler
Oaxaca cheese|Queso Oaxaca|lb|10|2 x 5 lb|cooler
Queso fresco|Queso fresco|lb|12|12 x 1 lb|cooler
Cotija cheese|Queso cotija|lb|10|2 x 5 lb|cooler
American cheese sliced|Queso americano rebanado|ea|640|4 x 160 slices|cooler
Cheddar sliced|Queso cheddar rebanado|ea|160|160 slices|cooler
Pepper jack sliced|Queso pepper jack rebanado|ea|160|160 slices|cooler
Swiss sliced|Queso suizo rebanado|ea|160|160 slices|cooler
Parmesan grated|Queso parmesano rallado|lb|5|5 lb bag|cooler
Nacho cheese sauce|Salsa de queso para nachos|can|6|6 x #10 can|dry
Sour cream|Crema agria|lb|5|5 lb tub|cooler
Mexican crema|Crema mexicana|qt|12|12 x 32 oz|cooler
Butter unsalted|Mantequilla sin sal|lb|36|36 x 1 lb|cooler
Butter salted|Mantequilla con sal|lb|36|36 x 1 lb|cooler
Butter pats|Mantequilla individual|ea|600|600 ct|cooler
Milk whole|Leche entera|gal|4|4 x 1 gal|cooler
Half and half|Media crema (half and half)|qt|12|12 x 1 qt|cooler
Heavy cream|Crema para batir|qt|12|12 x 1 qt|cooler
Oat milk|Leche de avena|qt|6|6 x 32 oz|cooler
Cream cheese|Queso crema|lb|10|10 x 1 lb / 3 lb loaf|cooler
Yogurt plain|Yogur natural|qt|6|6 x 32 oz|cooler
Coffee creamer cups|Cremas individuales|ea|400|400 ct|dry
## Produce
Limes|Limones|ea|200|~40 lb case (175-230 ct)|cooler
Lemons|Limones amarillos|ea|115|~40 lb case (115 ct)|cooler
Onions yellow|Cebolla amarilla|lb|50|50 lb sack|dry
Onions white|Cebolla blanca|lb|50|50 lb sack|dry
Onions red|Cebolla morada|lb|25|25 lb sack|dry
Tomatoes|Tomates|lb|25|25 lb case|cooler
Roma tomatoes|Tomate roma|lb|25|25 lb case|cooler
Cherry tomatoes|Tomate cherry|pt|12|12 pints|cooler
Tomatillos|Tomatillos|lb|25|25 lb case|cooler
Jalapenos|Chiles jalapenos|lb|10|10 lb case|cooler
Serrano peppers|Chiles serranos|lb|10|10 lb case|cooler
Poblano peppers|Chiles poblanos|lb|10|10 lb case|cooler
Habanero peppers|Chiles habaneros|lb|5|5 lb case|cooler
Bell peppers green|Pimiento verde|lb|25|25 lb case|cooler
Bell peppers red|Pimiento rojo|lb|11|11 lb case|cooler
Cilantro|Cilantro|bunch|30|30 bunches|cooler
Parsley|Perejil|bunch|30|30 bunches|cooler
Green onions|Cebollin|bunch|48|48 bunches|cooler
Garlic peeled|Ajo pelado|lb|5|5 lb jar|cooler
Garlic (whole heads)|Ajo (cabezas)|lb|5|5 lb bag|dry
Ginger root|Jengibre|lb|10|10 lb case|cooler
Avocados|Aguacates|ea|48|48 ct case|dry
Guacamole (frozen pulp)|Guacamole (pulpa congelada)|lb|12|6 x 2 lb|freezer
Lettuce iceberg|Lechuga iceberg|head|24|24 ct case|cooler
Lettuce shredded|Lechuga rallada|lb|5|5 lb bag|cooler
Romaine hearts|Corazones de lechuga romana|ea|48|48 ct (12 x 3)|cooler
Spring mix|Mezcla de hojas verdes|lb|3|3 lb case|cooler
Cabbage green|Repollo verde|lb|50|50 lb case|cooler
Cabbage red|Repollo morado|lb|50|50 lb case|cooler
Coleslaw mix|Mezcla para ensalada de col|lb|5|5 lb bag|cooler
Carrots|Zanahorias|lb|25|25 lb bag|cooler
Celery|Apio|ea|24|24 ct case|cooler
Cucumbers|Pepinos|ea|24|24 ct case|cooler
Radishes|Rabanos|lb|25|25 lb sack|cooler
Potatoes russet|Papa russet|lb|50|50 lb case|dry
Sweet potatoes|Camote|lb|40|40 lb case|dry
Corn on the cob|Elotes|ea|48|48 ct case|cooler
Mushrooms|Champinones|lb|10|10 lb case|cooler
Zucchini|Calabacita|lb|20|20 lb case|cooler
Pineapple|Pina|ea|7|7 ct case|dry
Pineapple chunks|Pina en trozos|lb|10|2 x 5 lb|cooler
Mangoes|Mangos|ea|12|12 ct case|dry
Watermelon|Sandia|ea|4|4 ct bin|dry
Strawberries|Fresas|lb|8|8 x 1 lb|cooler
Bananas|Platanos|lb|40|40 lb case|dry
Apples|Manzanas|ea|100|~40 lb case|cooler
Oranges|Naranjas|ea|88|~40 lb case|cooler
Pico de gallo (prepared)|Pico de gallo (preparado)|qt||house-made|prep
Pickled onions (prepared)|Cebolla encurtida (preparada)|qt||house-made|prep
Lime wedges (prepped)|Limones en gajos (preparados)|pan||house-made|prep
Diced onion (prepped)|Cebolla picada (preparada)|qt||house-made|prep
Chopped cilantro (prepped)|Cilantro picado (preparado)|qt||house-made|prep
## Tortillas & bread
Corn tortillas 6 in|Tortillas de maiz 6 in|pack|10|10 x 80 ct|dry
Corn tortillas street 4.5 in|Tortillas de maiz para taco 4.5 in|pack|12|12 x 90 ct|dry
Flour tortillas 6 in|Tortillas de harina 6 in|pack|12|12 x 24 ct|dry
Flour tortillas 10 in|Tortillas de harina 10 in|pack|12|12 x 12 ct|dry
Flour tortillas 12 in|Tortillas de harina 12 in|pack|12|12 x 12 ct|dry
Flour tortillas 14 in (burrito)|Tortillas de harina 14 in (burrito)|pack|12|12 x 10 ct|dry
Tostada shells|Tostadas|pack|12|12 x 10 ct|dry
Taco shells hard|Tacos dorados (conchas)|pack|8|8 x 25 ct|dry
Tortilla chips|Totopos|bag|6|6 x 2 lb bags|dry
Masa harina|Harina de maiz (masa)|lb|50|50 lb sack|dry
Fresh masa|Masa fresca|lb|10|10 lb bag|cooler
Burger buns 4 in|Pan para hamburguesa 4 in|pack|12|12 x 8 ct|dry
Brioche buns|Pan brioche|pack|6|6 x 8 ct|dry
Hot dog buns|Pan para hot dog|pack|12|12 x 8 ct|dry
Bolillo rolls|Bolillos|ea|60|60 ct|dry
Telera rolls (torta)|Teleras (tortas)|ea|48|48 ct|dry
Hoagie rolls|Pan para hoagie|ea|48|48 ct|dry
Sliced bread|Pan de caja|loaf|12|12 loaves|dry
Pita bread|Pan pita|pack|12|12 x 10 ct|dry
Naan|Naan|pack|12|12 x 5 ct|freezer
Pizza dough balls|Bolas de masa para pizza|ea|40|40 ct case|freezer
Bao buns|Pan bao|ea|60|60 ct|freezer
Waffle/funnel cake mix|Mezcla para waffles/funnel cake|lb|25|25 lb bag|dry
Pancake mix|Mezcla para hot cakes|lb|25|5 x 5 lb|dry
## Dry goods & pantry
Rice long grain|Arroz grano largo|lb|50|50 lb sack|dry
Rice jasmine|Arroz jazmin|lb|25|25 lb bag|dry
Rice sushi/calrose|Arroz calrose|lb|50|50 lb sack|dry
Black beans (can)|Frijoles negros (lata)|can|6|6 x #10 can|dry
Pinto beans (can)|Frijoles pintos (lata)|can|6|6 x #10 can|dry
Refried beans (can)|Frijoles refritos (lata)|can|6|6 x #10 can|dry
Pinto beans dry|Frijol pinto seco|lb|50|50 lb sack|dry
Black beans dry|Frijol negro seco|lb|25|25 lb sack|dry
Diced tomatoes (can)|Tomate picado (lata)|can|6|6 x #10 can|dry
Tomato paste (can)|Pure de tomate concentrado (lata)|can|6|6 x #10 can|dry
Crushed tomatoes (can)|Tomate triturado (lata)|can|6|6 x #10 can|dry
Pizza sauce (can)|Salsa para pizza (lata)|can|6|6 x #10 can|dry
Chipotle in adobo (can)|Chipotles en adobo (lata)|can|12|12 x 7 oz / 6 x #10|dry
Pickled jalapenos (can)|Jalapenos en escabeche (lata)|can|6|6 x #10 can|dry
Green chiles diced (can)|Chiles verdes picados (lata)|can|6|6 x #10 can|dry
Hominy (can)|Maiz pozolero (lata)|can|6|6 x #10 can|dry
Corn kernels (can)|Elote en grano (lata)|can|6|6 x #10 can|dry
Dried guajillo chiles|Chile guajillo seco|lb|5|5 lb bag|dry
Dried ancho chiles|Chile ancho seco|lb|5|5 lb bag|dry
Dried arbol chiles|Chile de arbol seco|lb|2|2 lb bag|dry
Flour all-purpose|Harina de trigo|lb|50|50 lb sack|dry
Panko breadcrumbs|Pan molido panko|lb|25|25 lb bag|dry
Cornmeal|Harina de maiz amarilla|lb|25|25 lb bag|dry
Cornstarch|Fecula de maiz|lb|24|24 x 1 lb|dry
Sugar granulated|Azucar|lb|50|50 lb sack|dry
Sugar brown|Azucar morena|lb|25|25 lb bag|dry
Powdered sugar|Azucar glass|lb|25|25 lb bag|dry
Sugar packets|Sobres de azucar|ea|2000|2000 ct|dry
Honey|Miel|lb|5|5 lb jug|dry
Maple syrup|Jarabe de maple|gal|4|4 x 1 gal|dry
Pasta (dry)|Pasta seca|lb|20|20 lb case|dry
Ramen noodles|Fideos ramen|pack|30|30 ct|dry
Peanut butter|Crema de cacahuate|lb|5|5 lb tub|dry
Chocolate chips|Chispas de chocolate|lb|25|25 lb case|dry
Cinnamon sugar|Azucar con canela|lb|5|5 lb|dry
Peanuts|Cacahuates|lb|25|25 lb case|dry
Popcorn kernels|Maiz palomero|lb|50|50 lb bag|dry
## Spices & seasonings
Salt kosher|Sal kosher|box|9|9 x 3 lb box|dry
Salt table|Sal de mesa|lb|24|24 x 26 oz|dry
Black pepper ground|Pimienta negra molida|lb|5|5 lb|dry
Garlic powder|Ajo en polvo|lb|5|5 lb|dry
Onion powder|Cebolla en polvo|lb|5|5 lb|dry
Cumin ground|Comino molido|lb|5|5 lb|dry
Chili powder|Chile en polvo|lb|5|5 lb|dry
Paprika|Paprika|lb|5|5 lb|dry
Smoked paprika|Paprika ahumada|lb|5|5 lb|dry
Oregano Mexican|Oregano mexicano|lb|1|1 lb|dry
Cayenne|Pimienta de cayena|lb|1|1 lb|dry
Taco seasoning|Sazonador para tacos|lb|5|5 lb|dry
Adobo seasoning|Sazonador adobo|lb|5|5 lb|dry
Achiote paste|Pasta de achiote|lb|12|12 x 1 lb|dry
Bay leaves|Hojas de laurel|oz|16|1 lb|dry
Cinnamon sticks|Canela en raja|lb|1|1 lb|dry
Tajin|Tajin|lb|5|5 lb|dry
Lemon pepper|Pimienta con limon|lb|5|5 lb|dry
Cajun seasoning|Sazonador cajun|lb|5|5 lb|dry
Bouillon chicken base|Consome de pollo|lb|12|12 x 1 lb|dry
Bouillon beef base|Consome de res|lb|12|12 x 1 lb|dry
MSG|Glutamato monosodico|lb|5|5 lb|dry
Sesame seeds|Ajonjoli|lb|5|5 lb|dry
## Sauces & condiments
Ketchup (bulk)|Catsup (granel)|can|6|6 x #10 can|dry
Ketchup packets|Sobres de catsup|ea|1000|1000 ct|dry
Mustard yellow|Mostaza amarilla|gal|4|4 x 1 gal|dry
Mustard packets|Sobres de mostaza|ea|500|500 ct|dry
Mayonnaise|Mayonesa|gal|4|4 x 1 gal|cooler
Mayo packets|Sobres de mayonesa|ea|500|500 ct|dry
Hot sauce bottles (table)|Salsa picante (botella de mesa)|bottle|24|24 x 5 oz|dry
Hot sauce gallon|Salsa picante (galon)|gal|4|4 x 1 gal|dry
Sriracha|Sriracha|bottle|12|12 x 28 oz|dry
Valentina sauce|Salsa Valentina|bottle|12|12 x 34 oz|dry
Salsa verde (prepared)|Salsa verde (preparada)|qt||house-made|prep
Salsa roja (prepared)|Salsa roja (preparada)|qt||house-made|prep
Salsa macha|Salsa macha|qt||house-made|prep
Guacamole (prepared)|Guacamole (preparado)|qt||house-made|prep
Chipotle mayo (prepared)|Mayonesa de chipotle (preparada)|qt||house-made|prep
BBQ sauce|Salsa BBQ|gal|4|4 x 1 gal|dry
Ranch dressing|Aderezo ranch|gal|4|4 x 1 gal|cooler
Ranch cups|Ranch en vasitos|ea|100|100 x 1.5 oz|cooler
Soy sauce|Salsa de soya|gal|4|4 x 1 gal|dry
Teriyaki sauce|Salsa teriyaki|gal|4|4 x 1 gal|dry
Buffalo wing sauce|Salsa buffalo|gal|4|4 x 1 gal|dry
Relish sweet|Relish dulce|gal|4|4 x 1 gal|cooler
Pickle chips|Pepinillos en rodajas|gal|4|4 x 1 gal|cooler
Sauerkraut|Chucrut|can|6|6 x #10 can|dry
Vinegar white|Vinagre blanco|gal|4|4 x 1 gal|dry
Lime juice|Jugo de limon|qt|12|12 x 32 oz|cooler
Mole paste|Pasta de mole|lb|12|12 x 1 lb|dry
Enchilada sauce|Salsa para enchiladas|can|6|6 x #10 can|dry
Chamoy|Chamoy|bottle|12|12 x 1 L|dry
Chocolate syrup|Jarabe de chocolate|bottle|12|12 x 24 oz|dry
Caramel sauce|Salsa de caramelo|bottle|12|12 x 24 oz|dry
Whipped cream cans|Crema batida en lata|can|12|12 x 15 oz|cooler
## Oils & fats
Fryer oil (soybean/canola)|Aceite para freidora|jug|1|35 lb jug (JIB)|dry
Canola oil|Aceite de canola|gal|6|6 x 1 gal|dry
Vegetable oil|Aceite vegetal|gal|6|6 x 1 gal|dry
Olive oil|Aceite de oliva|gal|4|4 x 1 gal|dry
Lard|Manteca de cerdo|lb|50|50 lb case|dry
Pan spray|Aceite en aerosol|can|6|6 x 17 oz|dry
Griddle butter alternative|Mantequilla liquida para plancha|gal|3|3 x 1 gal|dry
## Frozen
French fries|Papas fritas|bag|6|6 x 5 lb bags|freezer
Sweet potato fries|Papas de camote fritas|bag|6|6 x 2.5 lb bags|freezer
Tater tots|Papitas tots|bag|6|6 x 5 lb bags|freezer
Onion rings|Aros de cebolla|bag|4|4 x 2.5 lb|freezer
Hash browns|Papas hash brown|bag|6|6 x 3 lb|freezer
Churros|Churros|ea|300|300 ct case|freezer
Ice cream|Helado|tub|1|3 gal tub|freezer
Frozen corn|Elote congelado|lb|30|12 x 2.5 lb|freezer
Frozen peppers & onions|Pimientos y cebolla congelados|lb|20|10 x 2 lb|freezer
Frozen fruit mix|Fruta congelada|lb|20|4 x 5 lb|freezer
Ice (bagged)|Hielo (bolsa)|bag||20 lb bag|freezer
Dry ice|Hielo seco|lb||by the pound|outside
## Beverages
Bottled water 16.9 oz|Agua embotellada 500 ml|bottle|24|24 x 16.9 oz|dry
Soda cans assorted|Refrescos en lata|can|24|24 x 12 oz|dry
Mexican Coke (glass)|Coca-Cola mexicana (vidrio)|bottle|24|24 x 355 ml|dry
Jarritos assorted|Jarritos surtidos|bottle|24|24 x 12.5 oz|dry
Topo Chico|Topo Chico|bottle|24|24 x 12 oz|dry
Sports drink|Bebida deportiva|bottle|24|24 x 20 oz|dry
Juice boxes|Jugos en caja|ea|40|40 x 6.75 oz|dry
Lemonade concentrate|Concentrado de limonada|gal|4|4 x 1 gal|cooler
Horchata concentrate|Concentrado de horchata|gal|4|4 x 1 gal|cooler
Jamaica (hibiscus) dried|Flor de jamaica seca|lb|5|5 lb|dry
Iced tea bags|Te helado (bolsitas)|box|4|4 x 24 ct|dry
Coffee beans|Cafe en grano|lb|5|5 lb bag|dry
Coffee ground|Cafe molido|lb|5|5 lb bag|dry
Cold brew concentrate|Concentrado de cold brew|gal|4|4 x 1 gal|cooler
Hot cocoa mix|Chocolate en polvo|lb|5|5 lb|dry
Syrup vanilla|Jarabe de vainilla|bottle|12|12 x 750 ml|dry
Syrup caramel|Jarabe de caramelo|bottle|12|12 x 750 ml|dry
Soda syrup BIB|Jarabe de refresco (bag-in-box)|box|1|5 gal BIB|dry
CO2 tank|Tanque de CO2|tank||20 lb cylinder|outside
## Packaging & to-go
Foil taco wrap sheets|Hojas de aluminio para tacos|box|1|500 ct box|dry
Foil sheets 12x14|Hojas de aluminio 12x14|box|1|500 ct box|dry
Foil roll|Rollo de aluminio|roll|1|18 in x 500 ft|dry
Plastic wrap roll|Rollo de plastico|roll|1|18 in x 2000 ft|dry
Deli paper sheets|Papel encerado|box|1|1000 ct box|dry
Paper food trays #25|Charolas de papel #25|ea|1000|1000 ct case|dry
Paper food trays #50|Charolas de papel #50|ea|1000|1000 ct case|dry
Paper food trays #100|Charolas de papel #100|ea|500|500 ct case|dry
Paper food trays #250|Charolas de papel #250|ea|500|500 ct case|dry
Clamshell 9x9 (fiber)|Contenedor 9x9 (fibra)|ea|200|200 ct case|dry
Clamshell 9x6 (fiber)|Contenedor 9x6 (fibra)|ea|200|200 ct case|dry
Clamshell 6x6 (fiber)|Contenedor 6x6 (fibra)|ea|500|500 ct case|dry
Clamshell 3-compartment|Contenedor 3 divisiones|ea|200|200 ct case|dry
Burrito/foil bags|Bolsas de aluminio para burrito|ea|1000|1000 ct case|dry
Hot dog trays|Charolas para hot dog|ea|1000|1000 ct case|dry
Portion cups 2 oz|Vasitos 2 oz|sleeve|25|2500 ct (25 sleeves)|dry
Portion cup lids 2 oz|Tapas vasitos 2 oz|sleeve|25|2500 ct (25 sleeves)|dry
Portion cups 4 oz|Vasitos 4 oz|sleeve|25|2500 ct|dry
Portion cup lids 4 oz|Tapas vasitos 4 oz|sleeve|25|2500 ct|dry
Deli containers 16 oz|Contenedores deli 16 oz|ea|240|240 ct with lids|dry
Deli containers 32 oz|Contenedores deli 32 oz|ea|240|240 ct with lids|dry
Soup cups 12 oz with lids|Vasos para sopa 12 oz con tapa|ea|250|250 ct|dry
Hot cups 12 oz|Vasos calientes 12 oz|sleeve|20|1000 ct (20 sleeves)|dry
Hot cups 16 oz|Vasos calientes 16 oz|sleeve|20|1000 ct|dry
Hot cup lids|Tapas para vaso caliente|sleeve|10|1000 ct|dry
Cold cups 16 oz|Vasos frios 16 oz|sleeve|20|1000 ct|dry
Cold cups 24 oz|Vasos frios 24 oz|sleeve|10|600 ct|dry
Cold cup lids|Tapas para vaso frio|sleeve|10|1000 ct|dry
Cup sleeves|Fundas para vaso|ea|1000|1000 ct|dry
Cup carriers 4-cup|Portavasos 4|ea|300|300 ct|dry
Straws wrapped|Popotes envueltos|box|1|500 ct box|dry
Straws paper|Popotes de papel|box|1|500 ct box|dry
Napkins dispenser|Servilletas de dispensador|pack|24|24 x 250 (6000 ct)|dry
Napkins dinner|Servilletas grandes|ea|3000|3000 ct|dry
Forks wrapped|Tenedores envueltos|box|1|1000 ct|dry
Knives wrapped|Cuchillos envueltos|box|1|1000 ct|dry
Spoons wrapped|Cucharas envueltas|box|1|1000 ct|dry
Cutlery kits|Kits de cubiertos|box|1|250 ct|dry
Wooden forks|Tenedores de madera|box|1|1000 ct|dry
Toothpicks/skewers|Palillos/brochetas|box|1|1000 ct|dry
To-go bags small (paper)|Bolsas pequenas de papel|pack|1|500 ct|dry
To-go bags large (handle)|Bolsas grandes con asa|pack|1|250 ct|dry
T-shirt plastic bags|Bolsas de plastico camiseta|box|1|1000 ct|dry
Pizza boxes 14 in|Cajas para pizza 14 in|ea|50|50 ct bundle|dry
Pizza boxes 10 in|Cajas para pizza 10 in|ea|50|50 ct bundle|dry
Wax paper tissue|Papel de cera|box|1|1000 ct|dry
Labels/date dots|Etiquetas de fecha|roll|1|500 ct roll|dry
Receipt paper rolls|Rollos de papel para recibos|roll|50|50 rolls|dry
Sticker labels (brand)|Etiquetas con logo|roll|1|500 ct roll|dry
## Paper & cleaning supplies
Disposable gloves M|Guantes desechables M|box|10|10 x 100 ct|dry
Disposable gloves L|Guantes desechables L|box|10|10 x 100 ct|dry
Disposable gloves XL|Guantes desechables XL|box|10|10 x 100 ct|dry
Hair nets/caps|Redes para cabello|box|1|1000 ct|dry
Aprons disposable|Mandiles desechables|pack|1|100 ct|dry
Paper towels (roll)|Toallas de papel (rollo)|roll|12|12 rolls|dry
C-fold towels|Toallas C-fold|pack|16|16 x 150|dry
Toilet paper|Papel higienico|roll|80|80 rolls|dry
Trash bags 33 gal|Bolsas de basura 33 gal|box|1|100 ct|dry
Trash bags 55 gal|Bolsas de basura 55 gal|box|1|100 ct|dry
Dish soap|Jabon para trastes|gal|4|4 x 1 gal|dry
Hand soap|Jabon para manos|bottle|12|12 x 1 L|dry
Hand sanitizer|Gel antibacterial|bottle|12|12 x 1 L|dry
Sanitizer (quat)|Sanitizante (cuaternario)|gal|4|4 x 1 gal|dry
Sanitizer test strips|Tiras de prueba sanitizante|ea|1|1 vial|dry
Bleach|Cloro|gal|6|6 x 1 gal|dry
Degreaser|Desengrasante|gal|4|4 x 1 gal|dry
Glass cleaner|Limpiavidrios|bottle|12|12 x 32 oz|dry
Griddle cleaner|Limpiador de plancha|pack|10|10 packets|dry
Grill bricks/screens|Piedras/mallas para plancha|ea|12|12 ct|dry
Scrub pads|Fibras|pack|10|10 ct|dry
Steel wool|Fibra de acero|pack|12|12 ct|dry
Sponges|Esponjas|pack|10|10 ct|dry
Bar towels|Trapos|pack|1|25 ct|dry
Fryer oil filter paper|Papel filtro para freidora|box|1|100 ct|dry
Fryer boil-out|Limpiador de freidora|pack|20|20 packets|dry
Grease absorbent|Absorbente de grasa|bag|1|25 lb bag|outside
Pest control traps|Trampas para plagas|ea|12|12 ct|dry
First aid kit refill|Botiquin (recarga)|ea|1|1 kit|dry
Fire extinguisher (inspection)|Extintor (inspeccion)|ea||K-class / ABC|window
Thermometer probe covers|Cubiertas para termometro|box|1|100 ct|dry
## Propane & fuel
Propane tank 20 lb|Tanque de gas 20 lb|tank||20 lb cylinder|outside
Propane tank 30 lb|Tanque de gas 30 lb|tank||30 lb cylinder|outside
Propane tank 40 lb|Tanque de gas 40 lb|tank||40 lb cylinder|outside
Propane tank 100 lb|Tanque de gas 100 lb|tank||100 lb cylinder|outside
Generator fuel (gasoline)|Gasolina para generador|gal||jerry can|outside
Generator fuel (diesel)|Diesel para generador|gal||jerry can|outside
Generator oil|Aceite para generador|qt|12|12 x 1 qt|outside
Charcoal|Carbon|bag|1|20 lb bag|outside
Wood chips/chunks (smoker)|Lena/astillas para ahumar|bag|1|20 lb bag|outside
Sterno/chafing fuel|Combustible para chafer|can|24|24 ct|dry
Butane canisters|Cartuchos de butano|can|12|12 ct|outside
Fresh water (tank fill)|Agua potable (tanque)|gal||tank fill|outside
## Smallwares & misc
Hotel pan full 4 in|Bandeja hotel completa 4 in|pan||stainless|window
Hotel pan 1/3|Bandeja hotel 1/3|pan||stainless|window
Hotel pan 1/6|Bandeja hotel 1/6|pan||stainless|window
Hotel pan lids|Tapas para bandeja hotel|ea||various|window
Squeeze bottles|Botellas exprimibles|ea|12|12 ct|window
Tongs|Pinzas|ea||12 in|window
Spatulas|Espatulas|ea||various|window
Ladles/spoodles|Cucharones|ea||various|window
Cutting boards|Tablas para picar|ea||color-coded|window
Sharpies/markers|Marcadores|pack|12|12 ct|window
Masking/date tape|Cinta para fechar|roll|1|1 roll|window
Zip-top bags gallon|Bolsas ziploc galon|box|1|250 ct|dry
Zip-top bags quart|Bolsas ziploc cuarto|box|1|500 ct|dry
Food pan liners|Bolsas para bandejas|box|1|100 ct|dry
Parchment paper sheets|Papel pergamino|box|1|1000 ct|dry
Change (coins/small bills)|Cambio (monedas/billetes)|ea||cash drawer|window
Card reader paper/battery|Papel/bateria lector de tarjetas|ea||spares|window
"""

ZONES_DEFAULT = ("cooler", "freezer", "dry", "prep")


def _slug(s: str) -> str:
    import re
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def load() -> list[dict]:
    out = []
    cat = None
    for line in _RAW.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("## "):
            cat = line[3:].strip()
            continue
        name, es, unit, case_size, pack, zone = [p.strip() for p in line.split("|")]
        out.append({
            "id": "st-" + _slug(name),
            "name": name,
            "name_es": es,
            "category": cat,
            "unit": unit,
            "case_size": float(case_size) if case_size else None,
            "pack": pack,
            "zone": zone,
            "aliases": [es],
            "cost": None,
        })
    return out


CATALOG = load()
CATEGORIES = list(dict.fromkeys(c["category"] for c in CATALOG))
