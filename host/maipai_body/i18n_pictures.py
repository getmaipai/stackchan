# ruff: noqa: E501
"""Page words for the picture faces section, in the six page languages (firmware patches H03 and H04).

English and Spanish are the product languages; the other four are written for this item and not yet checked by a speaker.
"""

from __future__ import annotations

KEYS = (
    "settings.pics", "settings.pics.help", "settings.pics.mode", "settings.pics.mode.picture",
    "settings.pics.mode.overlay", "settings.pics.mode.sequence", "settings.pics.fps", "settings.pics.overlay",
    "settings.pics.color", "settings.pics.add", "settings.pics.remove", "settings.pics.send", "settings.pics.sending",
    "settings.pics.clear", "settings.pics.clear_ask", "settings.pics.used", "settings.pics.unreadable",
    "settings.pics.slot.neutral", "settings.pics.slot.happy", "settings.pics.slot.sad", "settings.pics.slot.angry",
    "settings.pics.slot.doubt", "settings.pics.slot.sleepy", "settings.pics.slot.speaking",
)  # fmt: skip

_TEXT: dict[str, tuple[str, ...]] = {
    "en": (
        "Picture face", "Use your own pictures as the face: one for each look. The pictures stay on this computer and go only to your unit.",
        "Style", "Picture only", "Picture with eyes and mouth drawn on top", "A short run of frames",
        "Frames per second", "Where the eyes and the mouth go, in pixels on the 320 by 240 picture (left eye x and y, right eye x and y, eye width and height, mouth x and y, mouth width and height) and their color",
        "Color of the eyes and mouth", "Choose a picture", "Remove", "Send to the unit", "Sending the pictures...",
        "Remove all pictures", "Remove every picture here and from the unit?", "Space used", "That picture could not be read. Choose a PNG or JPEG picture.",
        "Neutral", "Happy", "Sad", "Angry", "Doubtful", "Sleepy", "Speaking",
    ),
    "es": (
        "Cara con imágenes", "Usa tus propias imágenes como cara: una para cada gesto. Las imágenes se quedan en este ordenador y solo van a tu unidad.",
        "Estilo", "Solo la imagen", "Imagen con ojos y boca dibujados encima", "Una secuencia corta de cuadros",
        "Cuadros por segundo", "Dónde van los ojos y la boca, en píxeles sobre la imagen de 320 por 240 (ojo izquierdo x e y, ojo derecho x e y, ancho y alto del ojo, boca x e y, ancho y alto de la boca) y su color",
        "Color de los ojos y la boca", "Elegir una imagen", "Quitar", "Enviar a la unidad", "Enviando las imágenes...",
        "Quitar todas las imágenes", "¿Quitar todas las imágenes de aquí y de la unidad?", "Espacio usado", "No se pudo leer esa imagen. Elige una imagen PNG o JPEG.",
        "Neutral", "Contento", "Triste", "Enojado", "Dudoso", "Con sueño", "Hablando",
    ),
    "fr": (
        "Visage en images", "Utilisez vos propres images comme visage : une pour chaque expression. Les images restent sur cet ordinateur et vont seulement à votre unité.",
        "Style", "Image seule", "Image avec yeux et bouche dessinés dessus", "Une courte suite d'images",
        "Images par seconde", "Où vont les yeux et la bouche, en pixels sur l'image de 320 par 240 (œil gauche x et y, œil droit x et y, largeur et hauteur de l'œil, bouche x et y, largeur et hauteur de la bouche) et leur couleur",
        "Couleur des yeux et de la bouche", "Choisir une image", "Retirer", "Envoyer à l'unité", "Envoi des images...",
        "Retirer toutes les images", "Retirer toutes les images ici et sur l'unité ?", "Espace utilisé", "Cette image n'a pas pu être lue. Choisissez une image PNG ou JPEG.",
        "Neutre", "Content", "Triste", "En colère", "Dubitatif", "Endormi", "Qui parle",
    ),
    "de": (
        "Bildgesicht", "Verwenden Sie Ihre eigenen Bilder als Gesicht: eines für jeden Ausdruck. Die Bilder bleiben auf diesem Computer und gehen nur an Ihr Gerät.",
        "Stil", "Nur das Bild", "Bild mit aufgezeichneten Augen und Mund", "Eine kurze Bildfolge",
        "Bilder pro Sekunde", "Wo Augen und Mund liegen, in Pixeln auf dem Bild mit 320 mal 240 (linkes Auge x und y, rechtes Auge x und y, Breite und Höhe des Auges, Mund x und y, Breite und Höhe des Mundes) und ihre Farbe",
        "Farbe von Augen und Mund", "Bild wählen", "Entfernen", "An das Gerät senden", "Bilder werden gesendet...",
        "Alle Bilder entfernen", "Alle Bilder hier und auf dem Gerät entfernen?", "Belegter Platz", "Dieses Bild konnte nicht gelesen werden. Wählen Sie ein PNG- oder JPEG-Bild.",
        "Neutral", "Fröhlich", "Traurig", "Wütend", "Zweifelnd", "Müde", "Sprechend",
    ),
    "pt": (
        "Cara com imagens", "Use as suas próprias imagens como cara: uma para cada expressão. As imagens ficam neste computador e vão só para a sua unidade.",
        "Estilo", "Só a imagem", "Imagem com olhos e boca desenhados por cima", "Uma sequência curta de imagens",
        "Imagens por segundo", "Onde ficam os olhos e a boca, em pixels na imagem de 320 por 240 (olho esquerdo x e y, olho direito x e y, largura e altura do olho, boca x e y, largura e altura da boca) e a sua cor",
        "Cor dos olhos e da boca", "Escolher uma imagem", "Remover", "Enviar para a unidade", "A enviar as imagens...",
        "Remover todas as imagens", "Remover todas as imagens aqui e da unidade?", "Espaço usado", "Não foi possível ler essa imagem. Escolha uma imagem PNG ou JPEG.",
        "Neutra", "Contente", "Triste", "Zangada", "Duvidosa", "Sonolenta", "A falar",
    ),
    "it": (
        "Viso con immagini", "Usa le tue immagini come viso: una per ogni espressione. Le immagini restano su questo computer e vanno solo alla tua unità.",
        "Stile", "Solo l'immagine", "Immagine con occhi e bocca disegnati sopra", "Una breve sequenza di immagini",
        "Immagini al secondo", "Dove vanno occhi e bocca, in pixel sull'immagine da 320 per 240 (occhio sinistro x e y, occhio destro x e y, larghezza e altezza dell'occhio, bocca x e y, larghezza e altezza della bocca) e il loro colore",
        "Colore di occhi e bocca", "Scegli un'immagine", "Rimuovi", "Invia all'unità", "Invio delle immagini...",
        "Rimuovi tutte le immagini", "Rimuovere tutte le immagini da qui e dall'unità?", "Spazio usato", "Non è stato possibile leggere l'immagine. Scegli un'immagine PNG o JPEG.",
        "Neutra", "Contento", "Triste", "Arrabbiato", "Dubbioso", "Assonnato", "Mentre parla",
    ),
}  # fmt: skip

CATALOGS: dict[str, dict[str, str]] = {
    code: dict(zip(KEYS, text, strict=True)) for code, text in _TEXT.items()
}
