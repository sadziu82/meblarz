# GTV UA-337 preview geometry

`gtv_ua_337_160.obj` is converted from GTV's supplied UA-00-337160 3DS geometry,
not an independently dimensioned machining model. The aluminium and black finishes
share the same shape; colour is selected by the hardware library.

Source: https://assets.gtv.com.pl/assets/3D_solids/bryla_3d_obj/UA-00-337160.zip
(the archive labelled OBJ actually contains `UA-00-337160.3DS`).
Product: https://gtv.com.pl/produkt/UA-00-337160/
Drawing: https://assets.gtv.com.pl/assets/attachments/karta_produktowa/Karta_produktowa_PL-EN-RU__2021_270.pdf

Both supplied triangle objects are retained, including the mounting details.
Coordinates are normalized to [0,1]: X length, Y from outer grip toward the door,
Z strip width. The original world-space vertex bounds were approximately
180.005 × 24.554 × 26.453 mm; display scaling uses catalogue dimensions
180 × 25 × 26.5 mm. Drilling centres remain defined separately as 160 mm.
Vertical mounting rotates the mesh in the front plane, rather than stretching it.
The geometry belongs to GTV; no new asset licence is asserted here.
