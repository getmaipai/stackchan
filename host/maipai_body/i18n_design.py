# ruff: noqa: E501
"""Page words for the redesigned settings page, in the six page languages.

English and Spanish are the product languages; French, German, Portuguese and Italian are written for this
item and not yet checked by a speaker. Every key starts with ``settings.ui.`` and exists in all six.
"""

from __future__ import annotations

KEYS = (
    "nav.face", "nav.pictures", "nav.voice", "nav.time", "nav.reactions", "nav.games", "nav.people", "nav.privacy", "nav.system", "nav.units",
    "nav.label", "skip", "soon", "preview", "preview_note", "try_look", "retry", "theme.auto", "theme.light", "theme.dark", "theme.label",
    "net_error", "unit_offline", "units_label",
    "state.neutral", "state.happy", "state.sad", "state.angry", "state.thinking", "state.sleepy", "state.speaking", "state.love",
    "face.look", "face.effects", "face.effects_help", "face.overlays", "face.overlays_help", "face.thinking_tone", "face.clock24",
    "face.clock_style", "face.clock_digits", "face.clock_ring", "face.clock_idle", "face.never", "face.seconds",
    "face.band.morning", "face.band.day", "face.band.evening", "face.band.night", "face.hours_help", "face.tod_help", "face.captions_help",
    "voice.speed", "voice.pitch", "voice.volume", "voice.normal", "voice.quiet", "voice.quiet_help", "voice.mute_help", "voice.slow", "voice.fast",
    "time.timers", "time.timers_help", "time.alarms_help", "time.no_alarms", "time.remove", "time.zone_help",
    "day.mon", "day.tue", "day.wed", "day.thu", "day.fri", "day.sat", "day.sun",
    "react.words", "react.face", "react.sound", "react.extra", "react.dance", "react.add", "react.none",
    "games.empty", "games.best", "games.playing",
    "people.add", "people.empty_help",
    "privacy.lead", "privacy.camera", "privacy.camera_help",
    "system.check", "system.host", "system.update_help", "system.net_help",
    "units.title", "units.persona_help", "units.travel", "units.travel_help", "units.travel_key", "units.travel_send", "units.travel_forget", "units.travel_state", "units.travel_hidden", "cancel",
)  # fmt: skip

_TEXT: dict[str, tuple[str, ...]] = {
    "en": (
        "Face", "Pictures", "Voice", "Time", "Reactions", "Games", "People", "Privacy", "Updates", "Units",
        "Settings sections", "Skip to the settings", "Coming with the next unit update", "Live preview", "A drawing of the look you picked. The unit draws its own copy.", "Try a look", "Try again", "Match my device", "Light", "Dark", "Theme",
        "This page could not reach the host. Check that the host is still running, then try again.", "This unit is offline. Changes are saved here and sent when it reconnects.", "Your units",
        "Calm", "Happy", "Sad", "Angry", "Thinking", "Sleepy", "Talking", "Love",
        "Look", "Screen effects", "Scanlines, glow and a soft screen tint.", "Overlays", "Rain, snow and confetti over the face.", "Play a sound while thinking", "24 hour clock",
        "Clock look", "Digits", "Ring", "Show the clock after the unit is idle for", "Never", "seconds",
        "Morning", "Day", "Evening", "Night", "The hour each part of the day starts, from 0 to 23.", "The face gets calmer and dimmer as the day goes on.", "Words are shown on the screen while the unit talks.",
        "Speed", "Pitch", "Volume limit", "Normal", "Quiet hours", "The unit stays quiet and dim between two times you pick.", "A muted unit stops listening and talking until you turn this off.", "Slower", "Faster",
        "Timers", "Say: set a timer for five minutes. The countdown shows on the face and the unit chimes when it ends.", "The unit rings these every day you pick, even when no one is home.", "No alarms yet.", "Remove", "The unit gets its time from this computer and never asks the internet.",
        "Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun",
        "Words", "Face", "Sound", "Extra", "Dance", "Add a reaction", "none",
        "No scores yet. Say: let's play a game.", "Best", "A game is being played right now.",
        "Add a person", "Each person can have their own face colour, caption size and wake phrase.",
        "Nothing leaves your home. Your pictures, words and settings stay on this computer and your unit.", "Camera and microphone switches", "Turn the camera or microphone off for good.",
        "Check for updates", "This computer", "Checks the signed release first. Nothing is installed until you choose Install update.", "Checks Wi-Fi, the link to this computer and the private network, one step at a time.",
        "Your units", "A short note that tells this unit how to behave. Leave it empty for the built-in character.", "Travel key", "Take this unit to another Wi-Fi and it joins your private network by itself. Paste the key from your private network once.", "Paste the travel key", "Send the key", "Forget the key", "Status", "The key goes straight to the unit. It is never shown or kept on this computer.", "Cancel",
    ),
    "es": (
        "Cara", "Imágenes", "Voz", "Hora", "Reacciones", "Juegos", "Personas", "Privacidad", "Actualizar", "Unidades",
        "Secciones de ajustes", "Saltar a los ajustes", "Llega con la próxima actualización de la unidad", "Vista previa", "Un dibujo del gesto que elegiste. La unidad dibuja su propia copia.", "Prueba un gesto", "Intentar otra vez", "Igual que mi equipo", "Claro", "Oscuro", "Tema",
        "Esta página no pudo llegar al equipo. Comprueba que siga encendido y vuelve a intentarlo.", "Esta unidad no está conectada. Los cambios se guardan aquí y se envían cuando se reconecte.", "Tus unidades",
        "Tranquila", "Feliz", "Triste", "Enfadada", "Pensando", "Con sueño", "Hablando", "Amor",
        "Aspecto", "Efectos de pantalla", "Líneas de barrido, brillo y un tinte suave.", "Superposiciones", "Lluvia, nieve y confeti sobre la cara.", "Sonar mientras piensa", "Reloj de 24 horas",
        "Aspecto del reloj", "Números", "Anillo", "Mostrar el reloj tras estar en reposo", "Nunca", "segundos",
        "Mañana", "Día", "Tarde", "Noche", "La hora en que empieza cada parte del día, de 0 a 23.", "La cara se calma y se atenúa a medida que avanza el día.", "Las palabras se ven en la pantalla mientras la unidad habla.",
        "Velocidad", "Tono", "Límite de volumen", "Normal", "Horas de silencio", "La unidad se queda callada y tenue entre dos horas que elijas.", "Una unidad silenciada deja de escuchar y de hablar hasta que lo desactives.", "Más lenta", "Más rápida",
        "Temporizadores", "Di: pon un temporizador de cinco minutos. La cuenta atrás se ve en la cara y la unidad suena al terminar.", "La unidad suena estas alarmas los días que elijas, aunque no haya nadie en casa.", "Aún no hay alarmas.", "Quitar", "La unidad recibe la hora de este ordenador y nunca la pide a internet.",
        "Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom",
        "Palabras", "Cara", "Sonido", "Adorno", "Baile", "Añadir una reacción", "ninguno",
        "Aún no hay puntuaciones. Di: vamos a jugar.", "Mejor", "Ahora mismo se está jugando una partida.",
        "Añadir una persona", "Cada persona puede tener su propio color de cara, tamaño de subtítulos y frase de llamada.",
        "Nada sale de tu casa. Tus imágenes, palabras y ajustes se quedan en este ordenador y en tu unidad.", "Interruptores de cámara y micrófono", "Apaga la cámara o el micrófono del todo.",
        "Buscar actualizaciones", "Este ordenador", "Primero comprueba la versión firmada. No se instala nada hasta que elijas Instalar actualización.", "Comprueba el Wi-Fi, el enlace con este ordenador y la red privada, paso a paso.",
        "Tus unidades", "Una nota corta que dice a esta unidad cómo comportarse. Déjala vacía para el carácter incluido.", "Llave de viaje", "Lleva esta unidad a otro Wi-Fi y se une sola a tu red privada. Pega una vez la llave de tu red privada.", "Pega la llave de viaje", "Enviar la llave", "Olvidar la llave", "Estado", "La llave va directa a la unidad. Nunca se muestra ni se guarda en este ordenador.", "Cancelar",
    ),
    "fr": (
        "Visage", "Images", "Voix", "Heure", "Réactions", "Jeux", "Personnes", "Confidentialité", "Mises à jour", "Unités",
        "Sections des réglages", "Aller aux réglages", "Arrive avec la prochaine mise à jour de l'unité", "Aperçu en direct", "Un dessin du look choisi. L'unité dessine sa propre copie.", "Essayer un look", "Réessayer", "Comme mon appareil", "Clair", "Sombre", "Thème",
        "Cette page n'a pas pu joindre l'hôte. Vérifiez qu'il tourne toujours, puis réessayez.", "Cette unité est hors ligne. Les changements sont enregistrés ici et envoyés à sa reconnexion.", "Vos unités",
        "Calme", "Content", "Triste", "En colère", "Réflexion", "Endormi", "Parle", "Amour",
        "Look", "Effets d'écran", "Lignes de balayage, lueur et teinte douce.", "Superpositions", "Pluie, neige et confettis sur le visage.", "Jouer un son pendant la réflexion", "Horloge 24 heures",
        "Style de l'horloge", "Chiffres", "Anneau", "Afficher l'horloge après une inactivité de", "Jamais", "secondes",
        "Matin", "Jour", "Soir", "Nuit", "L'heure de début de chaque moment de la journée, de 0 à 23.", "Le visage devient plus calme et plus sombre au fil de la journée.", "Les mots s'affichent à l'écran pendant que l'unité parle.",
        "Vitesse", "Hauteur", "Limite de volume", "Normal", "Heures calmes", "L'unité reste silencieuse et tamisée entre deux heures de votre choix.", "Une unité en sourdine n'écoute plus et ne parle plus jusqu'à ce que vous la réactiviez.", "Plus lent", "Plus rapide",
        "Minuteurs", "Dites : mets un minuteur de cinq minutes. Le compte à rebours s'affiche sur le visage et l'unité sonne à la fin.", "L'unité sonne ces alarmes les jours choisis, même si personne n'est à la maison.", "Aucune alarme pour l'instant.", "Retirer", "L'unité reçoit l'heure de cet ordinateur et ne la demande jamais à internet.",
        "Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim",
        "Mots", "Visage", "Son", "Extra", "Danse", "Ajouter une réaction", "aucun",
        "Pas encore de scores. Dites : jouons à un jeu.", "Meilleur", "Une partie est en cours.",
        "Ajouter une personne", "Chaque personne peut avoir sa couleur de visage, sa taille de sous-titres et sa phrase d'appel.",
        "Rien ne quitte votre maison. Vos images, vos mots et vos réglages restent sur cet ordinateur et votre unité.", "Interrupteurs caméra et micro", "Coupez la caméra ou le micro pour de bon.",
        "Chercher des mises à jour", "Cet ordinateur", "La version signée est vérifiée d'abord. Rien n'est installé tant que vous ne choisissez pas Installer la mise à jour.", "Vérifie le Wi-Fi, le lien avec cet ordinateur et le réseau privé, étape par étape.",
        "Vos unités", "Une courte note qui dit à cette unité comment se comporter. Laissez vide pour le caractère intégré.", "Clé de voyage", "Emportez cette unité sur un autre Wi-Fi et elle rejoint seule votre réseau privé. Collez une fois la clé de votre réseau privé.", "Collez la clé de voyage", "Envoyer la clé", "Oublier la clé", "État", "La clé va directement à l'unité. Elle n'est jamais affichée ni conservée sur cet ordinateur.", "Annuler",
    ),
    "de": (
        "Gesicht", "Bilder", "Stimme", "Zeit", "Reaktionen", "Spiele", "Personen", "Datenschutz", "Updates", "Geräte",
        "Bereiche der Einstellungen", "Zu den Einstellungen springen", "Kommt mit dem nächsten Geräte-Update", "Live-Vorschau", "Eine Zeichnung des gewählten Aussehens. Das Gerät zeichnet seine eigene Kopie.", "Aussehen ausprobieren", "Erneut versuchen", "Wie mein Gerät", "Hell", "Dunkel", "Design",
        "Diese Seite konnte den Host nicht erreichen. Prüfen Sie, ob er noch läuft, und versuchen Sie es erneut.", "Dieses Gerät ist offline. Änderungen werden hier gespeichert und beim Wiederverbinden gesendet.", "Ihre Geräte",
        "Ruhig", "Fröhlich", "Traurig", "Wütend", "Denkt nach", "Müde", "Spricht", "Liebe",
        "Aussehen", "Bildschirmeffekte", "Scanlinien, Glühen und ein weicher Farbton.", "Überlagerungen", "Regen, Schnee und Konfetti über dem Gesicht.", "Beim Nachdenken einen Ton spielen", "24-Stunden-Uhr",
        "Uhr-Aussehen", "Ziffern", "Ring", "Uhr zeigen, wenn das Gerät so lange ruht:", "Nie", "Sekunden",
        "Morgen", "Tag", "Abend", "Nacht", "Die Stunde, zu der jeder Teil des Tages beginnt, von 0 bis 23.", "Das Gesicht wird im Lauf des Tages ruhiger und dunkler.", "Worte erscheinen auf dem Bildschirm, während das Gerät spricht.",
        "Tempo", "Tonhöhe", "Lautstärkegrenze", "Normal", "Ruhezeiten", "Das Gerät bleibt zwischen zwei gewählten Zeiten leise und gedimmt.", "Ein stummes Gerät hört und spricht nicht mehr, bis Sie das ausschalten.", "Langsamer", "Schneller",
        "Timer", "Sagen Sie: stell einen Timer auf fünf Minuten. Der Countdown erscheint im Gesicht und das Gerät läutet am Ende.", "Das Gerät läutet diese Wecker an den gewählten Tagen, auch wenn niemand zu Hause ist.", "Noch keine Wecker.", "Entfernen", "Das Gerät bekommt die Zeit von diesem Computer und fragt nie das Internet.",
        "Mo", "Di", "Mi", "Do", "Fr", "Sa", "So",
        "Worte", "Gesicht", "Ton", "Extra", "Tanz", "Reaktion hinzufügen", "keine",
        "Noch keine Punkte. Sagen Sie: lass uns spielen.", "Beste", "Gerade läuft ein Spiel.",
        "Person hinzufügen", "Jede Person kann eine eigene Gesichtsfarbe, Untertitelgröße und einen Weckruf haben.",
        "Nichts verlässt Ihr Zuhause. Ihre Bilder, Worte und Einstellungen bleiben auf diesem Computer und Ihrem Gerät.", "Schalter für Kamera und Mikrofon", "Kamera oder Mikrofon dauerhaft ausschalten.",
        "Nach Updates suchen", "Dieser Computer", "Zuerst wird die signierte Version geprüft. Nichts wird installiert, bis Sie Update installieren wählen.", "Prüft WLAN, die Verbindung zu diesem Computer und das private Netzwerk, Schritt für Schritt.",
        "Ihre Geräte", "Eine kurze Notiz, die diesem Gerät sagt, wie es sich verhält. Leer lassen für den eingebauten Charakter.", "Reiseschlüssel", "Nehmen Sie dieses Gerät in ein anderes WLAN mit, und es tritt allein Ihrem privaten Netzwerk bei. Fügen Sie den Schlüssel Ihres privaten Netzwerks einmal ein.", "Reiseschlüssel einfügen", "Schlüssel senden", "Schlüssel vergessen", "Status", "Der Schlüssel geht direkt an das Gerät. Er wird nie angezeigt oder auf diesem Computer gespeichert.", "Abbrechen",
    ),
    "pt": (
        "Rosto", "Imagens", "Voz", "Hora", "Reações", "Jogos", "Pessoas", "Privacidade", "Atualizações", "Unidades",
        "Seções das configurações", "Ir para as configurações", "Chega com a próxima atualização da unidade", "Pré-visualização ao vivo", "Um desenho do visual escolhido. A unidade desenha a sua própria cópia.", "Experimente um visual", "Tentar de novo", "Igual ao meu aparelho", "Claro", "Escuro", "Tema",
        "Esta página não conseguiu falar com o computador. Veja se ele continua ligado e tente de novo.", "Esta unidade está offline. As mudanças ficam salvas aqui e são enviadas quando ela voltar.", "Suas unidades",
        "Calmo", "Feliz", "Triste", "Bravo", "Pensando", "Com sono", "Falando", "Amor",
        "Visual", "Efeitos de tela", "Linhas de varredura, brilho e um tom suave.", "Sobreposições", "Chuva, neve e confete sobre o rosto.", "Tocar um som enquanto pensa", "Relógio de 24 horas",
        "Visual do relógio", "Números", "Anel", "Mostrar o relógio depois de ficar parada por", "Nunca", "segundos",
        "Manhã", "Dia", "Tarde", "Noite", "A hora em que cada parte do dia começa, de 0 a 23.", "O rosto fica mais calmo e mais escuro ao longo do dia.", "As palavras aparecem na tela enquanto a unidade fala.",
        "Velocidade", "Tom", "Limite de volume", "Normal", "Horário de silêncio", "A unidade fica quieta e com a tela escura entre dois horários que você escolher.", "Uma unidade silenciada para de ouvir e de falar até você desligar isto.", "Mais lenta", "Mais rápida",
        "Temporizadores", "Diga: coloque um temporizador de cinco minutos. A contagem aparece no rosto e a unidade toca no fim.", "A unidade toca estes alarmes nos dias que você escolher, mesmo sem ninguém em casa.", "Ainda não há alarmes.", "Remover", "A unidade recebe a hora deste computador e nunca pergunta à internet.",
        "Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom",
        "Palavras", "Rosto", "Som", "Extra", "Dança", "Adicionar uma reação", "nenhum",
        "Ainda não há pontuações. Diga: vamos jogar.", "Melhor", "Um jogo está em andamento agora.",
        "Adicionar uma pessoa", "Cada pessoa pode ter a sua cor de rosto, tamanho de legenda e frase de chamada.",
        "Nada sai da sua casa. Suas imagens, palavras e configurações ficam neste computador e na sua unidade.", "Chaves de câmera e microfone", "Desligue a câmera ou o microfone de vez.",
        "Procurar atualizações", "Este computador", "Primeiro verifica a versão assinada. Nada é instalado até você escolher Instalar atualização.", "Verifica o Wi-Fi, o link com este computador e a rede privada, passo a passo.",
        "Suas unidades", "Uma nota curta que diz a esta unidade como se comportar. Deixe vazio para o caráter embutido.", "Chave de viagem", "Leve esta unidade para outro Wi-Fi e ela entra sozinha na sua rede privada. Cole uma vez a chave da sua rede privada.", "Cole a chave de viagem", "Enviar a chave", "Esquecer a chave", "Estado", "A chave vai direto para a unidade. Nunca é mostrada nem guardada neste computador.", "Cancelar",
    ),
    "it": (
        "Viso", "Immagini", "Voce", "Ora", "Reazioni", "Giochi", "Persone", "Privacy", "Aggiornamenti", "Unità",
        "Sezioni delle impostazioni", "Vai alle impostazioni", "Arriva con il prossimo aggiornamento dell'unità", "Anteprima dal vivo", "Un disegno dell'aspetto scelto. L'unità disegna la sua copia.", "Prova un aspetto", "Riprova", "Come il mio dispositivo", "Chiaro", "Scuro", "Tema",
        "Questa pagina non ha raggiunto il computer. Controlla che sia ancora acceso e riprova.", "Questa unità è offline. Le modifiche sono salvate qui e inviate quando si riconnette.", "Le tue unità",
        "Calmo", "Felice", "Triste", "Arrabbiato", "Pensa", "Assonnato", "Parla", "Amore",
        "Aspetto", "Effetti dello schermo", "Linee di scansione, bagliore e una tinta morbida.", "Sovrapposizioni", "Pioggia, neve e coriandoli sul viso.", "Suona mentre pensa", "Orologio a 24 ore",
        "Aspetto dell'orologio", "Cifre", "Anello", "Mostra l'orologio dopo che l'unità è ferma per", "Mai", "secondi",
        "Mattina", "Giorno", "Sera", "Notte", "L'ora in cui inizia ogni parte della giornata, da 0 a 23.", "Il viso diventa più calmo e più scuro col passare della giornata.", "Le parole compaiono sullo schermo mentre l'unità parla.",
        "Velocità", "Tono", "Limite del volume", "Normale", "Ore di silenzio", "L'unità resta zitta e soffusa tra due orari che scegli.", "Un'unità muta smette di ascoltare e parlare finché non lo disattivi.", "Più lenta", "Più veloce",
        "Timer", "Di': imposta un timer di cinque minuti. Il conto alla rovescia compare sul viso e l'unità suona alla fine.", "L'unità suona queste sveglie nei giorni scelti, anche se non c'è nessuno in casa.", "Ancora nessuna sveglia.", "Rimuovi", "L'unità riceve l'ora da questo computer e non la chiede mai a internet.",
        "Lun", "Mar", "Mer", "Gio", "Ven", "Sab", "Dom",
        "Parole", "Viso", "Suono", "Extra", "Ballo", "Aggiungi una reazione", "nessuno",
        "Ancora nessun punteggio. Di': giochiamo.", "Migliore", "Una partita è in corso adesso.",
        "Aggiungi una persona", "Ogni persona può avere il proprio colore del viso, la dimensione dei sottotitoli e la frase di richiamo.",
        "Niente lascia la tua casa. Le tue immagini, parole e impostazioni restano su questo computer e sulla tua unità.", "Interruttori di fotocamera e microfono", "Spegni la fotocamera o il microfono per sempre.",
        "Cerca aggiornamenti", "Questo computer", "Prima controlla la versione firmata. Non si installa nulla finché non scegli Installa aggiornamento.", "Controlla il Wi-Fi, il collegamento con questo computer e la rete privata, un passo alla volta.",
        "Le tue unità", "Una breve nota che dice a questa unità come comportarsi. Lascia vuoto per il carattere incluso.", "Chiave di viaggio", "Porta questa unità su un altro Wi-Fi e si unisce da sola alla tua rete privata. Incolla una volta la chiave della tua rete privata.", "Incolla la chiave di viaggio", "Invia la chiave", "Dimentica la chiave", "Stato", "La chiave va dritta all'unità. Non viene mai mostrata né conservata su questo computer.", "Annulla",
    ),
}  # fmt: skip

CATALOGS: dict[str, dict[str, str]] = {
    code: {f"settings.ui.{k}": v for k, v in zip(KEYS, words, strict=True)}
    for code, words in _TEXT.items()
}

# ---- the everyday device controls and the first-level groups (added with the owner's full settings list) ----

KEYS2 = (
    "g.home", "g.look", "g.voice", "g.network", "g.behaviour", "g.play", "g.system",
    "home.battery", "home.charging", "home.face", "home.room_light", "home.paired",
    "look.brightness", "look.brightness_help", "look.auto", "look.night_dim", "look.led", "look.led_help", "look.led_off", "look.led_bright",
    "voice.volume_now", "voice.speaker_mute", "voice.mic_mute", "voice.wake", "voice.wake_sens", "voice.stop_word", "voice.wake_help",
    "net.current", "net.signal", "net.join", "net.join_help", "net.private", "net.private_on", "net.hub_addr", "net.sig.strong", "net.sig.ok", "net.sig.weak", "net.paired", "net.pair_help",
    "beh.head", "beh.head_help", "beh.sleep", "beh.sleep_help", "beh.vision", "beh.vision_help", "beh.quiet_mode", "beh.quiet_mode_help",
    "sys.restart", "sys.restart_help", "sys.reset", "sys.reset_help", "sys.reset_type", "sys.reset_go", "sys.memory", "sys.storage", "sys.free", "sys.lowest",
)  # fmt: skip

_TEXT2: dict[str, tuple[str, ...]] = {
    "en": (
        "Home", "Look", "Voice and sound", "Network", "Behaviour", "Games and fun", "System",
        "Battery", "Charging", "Face right now", "Room light", "Paired with",
        "Screen brightness", "How bright the screen is. It never goes fully dark, so you can always find the unit.", "Adjust to the room light", "Dim the screen at night", "Light ring", "The colour of the light ring.", "Off", "Ring brightness",
        "Volume", "Speaker mute", "Microphone mute", "Wake word", "Wake word sensitivity", "Stop word", "Choose whether the unit wakes to its name and how easily it hears it.",
        "Current network", "Signal", "Join a new network", "Opens the unit's own setup window. On your phone, join the hotspot the unit shows, then pick the new Wi-Fi. Saved networks are never listed here.", "Private network", "Use the private network when away", "Private address of this computer", "Strong", "Good", "Weak", "Paired with this computer", "To pair a unit, run stackchan pair on this computer, then type the code on the unit.",
        "Head movement", "Lets the unit turn its head to look at you and around the room.", "Sleep and screen timeout", "How long the unit waits before the screen dims and it goes to sleep.", "Camera", "Turn the camera off. The unit stops looking for faces.", "Full quiet", "No sound, no listening and no movement until you turn this off.",
        "Restart the unit", "Restarts the unit and keeps every setting.", "Reset the unit", "Erases the unit's saved Wi-Fi and settings. It then needs setting up again.", "Type RESET to confirm", "Reset the unit", "Memory", "Storage", "free", "lowest so far",
    ),
    "es": (
        "Inicio", "Aspecto", "Voz y sonido", "Red", "Comportamiento", "Juegos y diversión", "Sistema",
        "Batería", "Cargando", "Cara ahora mismo", "Luz de la habitación", "Emparejada con",
        "Brillo de la pantalla", "Cuánta luz da la pantalla. Nunca se apaga del todo, para que siempre encuentres la unidad.", "Ajustar a la luz de la habitación", "Atenuar la pantalla de noche", "Anillo de luz", "El color del anillo de luz.", "Apagado", "Brillo del anillo",
        "Volumen", "Silenciar altavoz", "Silenciar micrófono", "Palabra de llamada", "Sensibilidad de la palabra de llamada", "Palabra de parada", "Elige si la unidad despierta con su nombre y con qué facilidad lo oye.",
        "Red actual", "Señal", "Unirse a otra red", "Abre la ventana de configuración de la unidad. En tu teléfono, únete a la red que muestra la unidad y elige el nuevo Wi-Fi. Aquí nunca se listan las redes guardadas.", "Red privada", "Usar la red privada fuera de casa", "Dirección privada de este ordenador", "Fuerte", "Buena", "Débil", "Emparejada con este ordenador", "Para emparejar una unidad, ejecuta stackchan pair en este ordenador y escribe el código en la unidad.",
        "Movimiento de la cabeza", "Deja que la unidad gire la cabeza para mirarte y mirar la habitación.", "Reposo y tiempo de pantalla", "Cuánto espera la unidad antes de atenuar la pantalla y dormirse.", "Cámara", "Apaga la cámara. La unidad deja de buscar caras.", "Silencio total", "Sin sonido, sin escuchar y sin moverse hasta que lo desactives.",
        "Reiniciar la unidad", "Reinicia la unidad y conserva todos los ajustes.", "Restablecer la unidad", "Borra el Wi-Fi y los ajustes guardados de la unidad. Después hay que configurarla otra vez.", "Escribe RESET para confirmar", "Restablecer la unidad", "Memoria", "Almacenamiento", "libre", "mínimo hasta ahora",
    ),
    "fr": (
        "Accueil", "Look", "Voix et son", "Réseau", "Comportement", "Jeux et détente", "Système",
        "Batterie", "En charge", "Visage en ce moment", "Lumière de la pièce", "Appairée avec",
        "Luminosité de l'écran", "La luminosité de l'écran. Il ne s'éteint jamais tout à fait, pour que vous trouviez toujours l'unité.", "S'adapter à la lumière de la pièce", "Tamiser l'écran la nuit", "Anneau lumineux", "La couleur de l'anneau lumineux.", "Éteint", "Luminosité de l'anneau",
        "Volume", "Haut-parleur en sourdine", "Micro en sourdine", "Mot d'appel", "Sensibilité du mot d'appel", "Mot d'arrêt", "Choisissez si l'unité s'éveille à son nom et avec quelle facilité elle l'entend.",
        "Réseau actuel", "Signal", "Rejoindre un nouveau réseau", "Ouvre la fenêtre de configuration de l'unité. Sur votre téléphone, rejoignez le point d'accès affiché par l'unité, puis choisissez le nouveau Wi-Fi. Les réseaux enregistrés ne sont jamais listés ici.", "Réseau privé", "Utiliser le réseau privé hors de la maison", "Adresse privée de cet ordinateur", "Fort", "Bon", "Faible", "Appairée avec cet ordinateur", "Pour appairer une unité, lancez stackchan pair sur cet ordinateur, puis tapez le code sur l'unité.",
        "Mouvement de la tête", "Laisse l'unité tourner la tête pour vous regarder et regarder la pièce.", "Veille et délai d'écran", "Combien de temps l'unité attend avant de tamiser l'écran et de s'endormir.", "Caméra", "Coupe la caméra. L'unité ne cherche plus les visages.", "Silence total", "Ni son, ni écoute, ni mouvement jusqu'à ce que vous le désactiviez.",
        "Redémarrer l'unité", "Redémarre l'unité et garde tous les réglages.", "Réinitialiser l'unité", "Efface le Wi-Fi et les réglages enregistrés de l'unité. Il faut ensuite la configurer de nouveau.", "Tapez RESET pour confirmer", "Réinitialiser l'unité", "Mémoire", "Stockage", "libre", "minimum jusqu'ici",
    ),
    "de": (
        "Start", "Aussehen", "Stimme und Ton", "Netzwerk", "Verhalten", "Spiele und Spaß", "System",
        "Akku", "Lädt", "Gesicht gerade jetzt", "Raumlicht", "Gekoppelt mit",
        "Bildschirmhelligkeit", "Wie hell der Bildschirm ist. Er wird nie ganz dunkel, damit Sie das Gerät immer finden.", "An das Raumlicht anpassen", "Bildschirm nachts dimmen", "Leuchtring", "Die Farbe des Leuchtrings.", "Aus", "Helligkeit des Rings",
        "Lautstärke", "Lautsprecher stumm", "Mikrofon stumm", "Weckwort", "Empfindlichkeit des Weckworts", "Stoppwort", "Wählen Sie, ob das Gerät auf seinen Namen reagiert und wie leicht es ihn hört.",
        "Aktuelles Netzwerk", "Signal", "Neues Netzwerk verbinden", "Öffnet das Einrichtungsfenster des Geräts. Verbinden Sie Ihr Telefon mit dem Hotspot, den das Gerät zeigt, und wählen Sie dann das neue WLAN. Gespeicherte Netzwerke werden hier nie aufgelistet.", "Privates Netzwerk", "Privates Netzwerk unterwegs nutzen", "Private Adresse dieses Computers", "Stark", "Gut", "Schwach", "Mit diesem Computer gekoppelt", "Zum Koppeln führen Sie stackchan pair auf diesem Computer aus und geben den Code am Gerät ein.",
        "Kopfbewegung", "Das Gerät dreht den Kopf, um Sie und den Raum anzusehen.", "Ruhezustand und Bildschirm-Timeout", "Wie lange das Gerät wartet, bevor der Bildschirm dunkler wird und es schläft.", "Kamera", "Schaltet die Kamera aus. Das Gerät sucht keine Gesichter mehr.", "Volle Ruhe", "Kein Ton, kein Zuhören und keine Bewegung, bis Sie das ausschalten.",
        "Gerät neu starten", "Startet das Gerät neu und behält alle Einstellungen.", "Gerät zurücksetzen", "Löscht das gespeicherte WLAN und die Einstellungen des Geräts. Danach muss es neu eingerichtet werden.", "Tippen Sie RESET zur Bestätigung", "Gerät zurücksetzen", "Speicher", "Ablage", "frei", "niedrigster Stand",
    ),
    "pt": (
        "Início", "Visual", "Voz e som", "Rede", "Comportamento", "Jogos e diversão", "Sistema",
        "Bateria", "Carregando", "Rosto agora", "Luz do ambiente", "Pareada com",
        "Brilho da tela", "Quanto brilha a tela. Ela nunca apaga por completo, para você sempre achar a unidade.", "Ajustar à luz do ambiente", "Escurecer a tela à noite", "Anel de luz", "A cor do anel de luz.", "Desligado", "Brilho do anel",
        "Volume", "Silenciar alto-falante", "Silenciar microfone", "Palavra de chamada", "Sensibilidade da palavra de chamada", "Palavra de parada", "Escolha se a unidade acorda com o seu nome e com que facilidade o ouve.",
        "Rede atual", "Sinal", "Entrar em uma nova rede", "Abre a janela de configuração da unidade. No celular, entre no ponto de acesso que a unidade mostra e escolha o novo Wi-Fi. As redes salvas nunca são listadas aqui.", "Rede privada", "Usar a rede privada fora de casa", "Endereço privado deste computador", "Forte", "Boa", "Fraca", "Pareada com este computador", "Para parear uma unidade, rode stackchan pair neste computador e digite o código na unidade.",
        "Movimento da cabeça", "Deixa a unidade virar a cabeça para olhar você e o ambiente.", "Repouso e tempo de tela", "Quanto a unidade espera antes de escurecer a tela e dormir.", "Câmera", "Desliga a câmera. A unidade deixa de procurar rostos.", "Silêncio total", "Sem som, sem ouvir e sem se mover até você desligar isto.",
        "Reiniciar a unidade", "Reinicia a unidade e mantém todas as configurações.", "Restaurar a unidade", "Apaga o Wi-Fi e as configurações salvas da unidade. Depois ela precisa ser configurada de novo.", "Digite RESET para confirmar", "Restaurar a unidade", "Memória", "Armazenamento", "livre", "menor até agora",
    ),
    "it": (
        "Home", "Aspetto", "Voce e suono", "Rete", "Comportamento", "Giochi e svago", "Sistema",
        "Batteria", "In carica", "Viso in questo momento", "Luce della stanza", "Abbinata con",
        "Luminosità dello schermo", "Quanto è luminoso lo schermo. Non si spegne mai del tutto, così trovi sempre l'unità.", "Adatta alla luce della stanza", "Attenua lo schermo di notte", "Anello luminoso", "Il colore dell'anello luminoso.", "Spento", "Luminosità dell'anello",
        "Volume", "Silenzia altoparlante", "Silenzia microfono", "Parola di richiamo", "Sensibilità della parola di richiamo", "Parola di stop", "Scegli se l'unità si sveglia al suo nome e con che facilità lo sente.",
        "Rete attuale", "Segnale", "Unisciti a una nuova rete", "Apre la finestra di configurazione dell'unità. Sul telefono unisciti all'hotspot mostrato dall'unità, poi scegli il nuovo Wi-Fi. Le reti salvate non vengono mai elencate qui.", "Rete privata", "Usa la rete privata fuori casa", "Indirizzo privato di questo computer", "Forte", "Buono", "Debole", "Abbinata a questo computer", "Per abbinare un'unità, esegui stackchan pair su questo computer e digita il codice sull'unità.",
        "Movimento della testa", "Lascia che l'unità giri la testa per guardarti e guardare la stanza.", "Riposo e timeout dello schermo", "Quanto aspetta l'unità prima di attenuare lo schermo e addormentarsi.", "Fotocamera", "Spegne la fotocamera. L'unità non cerca più volti.", "Silenzio totale", "Niente suono, niente ascolto e niente movimento finché non lo disattivi.",
        "Riavvia l'unità", "Riavvia l'unità e mantiene tutte le impostazioni.", "Ripristina l'unità", "Cancella il Wi-Fi e le impostazioni salvate dell'unità. Poi va configurata di nuovo.", "Scrivi RESET per confermare", "Ripristina l'unità", "Memoria", "Archivio", "libero", "minimo finora",
    ),
}  # fmt: skip

for _code, _words in _TEXT2.items():
    CATALOGS[_code].update({f"settings.ui.{k}": v for k, v in zip(KEYS2, _words, strict=True)})

# ---- Tailscale wording, About, and the Remote page (owner feedback 2026-11-16) ----

KEYS3 = (
    "ts.step1", "ts.step1_link", "ts.step2", "ts.step3", "ts.happens", "ts.h1", "ts.h2", "ts.h3", "ts.h4", "ts.peer_save",
    "ts.state.off", "ts.state.waiting", "ts.state.connecting", "ts.state.connected", "ts.state.error",
    "ts.addr", "ts.route", "ts.route.home", "ts.route.private", "ts.last_error",
    "ts.err.bad_key", "ts.err.bad_address", "ts.err.not_compiled", "ts.err.running_restart_first", "ts.err.refusal",
    "ts.test", "ts.test.ok", "ts.test.ready", "ts.test.nokey", "ts.about", "ts.about_body", "ts.guide",
    "sys.about", "sys.source", "sys.source_note", "sys.host_version", "sys.licence", "sys.docs",
    "g.remote", "rem.quick", "rem.beep", "rem.flash", "rem.find", "rem.find_stop", "rem.say", "rem.say_label", "rem.say_go", "rem.pad", "rem.center",
    "rem.look", "rem.nod", "rem.shake", "rem.dance", "rem.dance_go", "rem.dance_stop", "rem.game", "rem.game_go", "rem.photo", "rem.photo_need", "rem.photo_alt",
    "rem.mute", "rem.unmute", "rem.restart", "rem.done", "rem.offline", "rem.limits", "rem.working", "rem.find_on",
)  # fmt: skip

_TEXT3: dict[str, tuple[str, ...]] = {
    "en": (
        "In your Tailscale admin console, make an auth key: one-time (reusable off) and tagged.", "Open the Tailscale keys page", "Paste the key here and send it to the unit.", "Type your home hub's Tailscale address and save it.", "What happens", "The unit joins your Tailscale network only when it cannot reach the hub.", "At home it never starts.", "The key is erased from the unit after it joins.", "Nothing goes to MaiPai.", "Save the address",
        "Off", "Waiting", "Connecting", "Connected", "Problem",
        "The unit's Tailscale address", "The hub link goes through", "Your home network", "Tailscale", "Last problem",
        "The key was not accepted. Make a new one-time key and paste it again.", "The hub address is not valid. Use the form 100.x.x.x and save again.", "This unit's firmware was built without Tailscale. Update the firmware, then try again.", "The unit is joining right now. Restart it, then forget the key.", "The unit is short of free working space. Try again in a minute.",
        "Test", "Working. The unit is on your Tailscale network and the hub link uses it.", "Ready. The unit joins Tailscale only if it cannot reach the hub.", "Add an auth key and the hub's address first, then test again.", "About this", "Tailscale joins your own devices into one private network. The unit asks it for a route to your home hub only when it is away from home. Your voice, pictures and settings go from the unit to your hub and nowhere else.", "Read the full guide",
        "About", "Source code and docs", "Open source: free to read, use and change.", "Host version", "Licence", "User docs",
        "Remote", "Quick actions", "Beep", "Flash lights", "Find my robot", "Stop finding", "Say something", "Words to say", "Speak", "Head pad", "Center",
        "Look around", "Nod yes", "Shake no", "Dance", "Dance now", "Stop the dance", "Start a game", "Play", "Take a picture", "Needs the camera build", "The picture the unit just took",
        "Mute", "Unmute", "Restart", "Done.", "This unit is offline. Turn it on and bring it near the router, then try again.", "Head limits: left and right 128 degrees, up and down 5 to 85 degrees.", "Working...", "The robot is beeping and flashing until you stop it.",
    ),
    "es": (
        "En tu consola de administración de Tailscale, crea una clave de autenticación: de un solo uso y con etiqueta.", "Abrir la página de claves de Tailscale", "Pega la clave aquí y envíala a la unidad.", "Escribe la dirección de Tailscale de tu hub en casa y guárdala.", "Qué pasa", "La unidad se une a tu red de Tailscale solo cuando no llega al hub.", "En casa nunca se inicia.", "La clave se borra de la unidad después de unirse.", "Nada va a MaiPai.", "Guardar la dirección",
        "Apagado", "Esperando", "Conectando", "Conectada", "Problema",
        "Dirección de Tailscale de la unidad", "El enlace con el hub pasa por", "Tu red de casa", "Tailscale", "Último problema",
        "No se aceptó la clave. Crea una clave nueva de un solo uso y pégala otra vez.", "La dirección del hub no es válida. Usa el formato 100.x.x.x y guarda otra vez.", "El firmware de esta unidad se creó sin Tailscale. Actualiza el firmware y vuelve a intentarlo.", "La unidad se está uniendo ahora. Reinicia la unidad y luego olvida la clave.", "A la unidad le falta espacio libre de trabajo. Inténtalo de nuevo en un minuto.",
        "Probar", "Funciona. La unidad está en tu red de Tailscale y el enlace con el hub la usa.", "Lista. La unidad se une a Tailscale solo si no llega al hub.", "Primero añade una clave y la dirección del hub, y prueba otra vez.", "Acerca de esto", "Tailscale une tus propios dispositivos en una red privada. La unidad le pide una ruta a tu hub en casa solo cuando está fuera de casa. Tu voz, imágenes y ajustes van de la unidad a tu hub y a ningún otro sitio.", "Leer la guía completa",
        "Acerca de", "Código fuente y documentación", "Código abierto: libre para leer, usar y cambiar.", "Versión del equipo", "Licencia", "Documentación de uso",
        "Remoto", "Acciones rápidas", "Pitido", "Parpadear luces", "Encontrar mi robot", "Dejar de buscar", "Decir algo", "Palabras para decir", "Hablar", "Panel de cabeza", "Centrar",
        "Mirar alrededor", "Decir sí", "Decir no", "Bailar", "Bailar ahora", "Parar el baile", "Empezar un juego", "Jugar", "Hacer una foto", "Necesita la versión con cámara", "La foto que acaba de hacer la unidad",
        "Silenciar", "Quitar silencio", "Reiniciar", "Hecho.", "Esta unidad no está conectada. Enciéndela y acércala al router, y vuelve a intentarlo.", "Límites de la cabeza: izquierda y derecha 128 grados, arriba y abajo de 5 a 85 grados.", "Trabajando...", "El robot suena y parpadea hasta que lo pares.",
    ),
    "fr": (
        "Dans votre console d'administration Tailscale, créez une clé d'authentification : à usage unique et étiquetée.", "Ouvrir la page des clés Tailscale", "Collez la clé ici et envoyez-la à l'unité.", "Tapez l'adresse Tailscale de votre hub à la maison et enregistrez-la.", "Ce qui se passe", "L'unité rejoint votre réseau Tailscale seulement quand elle ne peut pas joindre le hub.", "À la maison, elle ne démarre jamais.", "La clé est effacée de l'unité après la connexion.", "Rien ne part vers MaiPai.", "Enregistrer l'adresse",
        "Désactivé", "En attente", "Connexion", "Connectée", "Problème",
        "Adresse Tailscale de l'unité", "Le lien avec le hub passe par", "Votre réseau domestique", "Tailscale", "Dernier problème",
        "La clé n'a pas été acceptée. Créez une nouvelle clé à usage unique et collez-la de nouveau.", "L'adresse du hub n'est pas valide. Utilisez la forme 100.x.x.x et enregistrez de nouveau.", "Le firmware de cette unité a été construit sans Tailscale. Mettez-le à jour, puis réessayez.", "L'unité se connecte en ce moment. Redémarrez-la, puis oubliez la clé.", "L'unité manque d'espace de travail libre. Réessayez dans une minute.",
        "Tester", "Ça marche. L'unité est sur votre réseau Tailscale et le lien avec le hub l'utilise.", "Prête. L'unité rejoint Tailscale seulement si elle ne peut pas joindre le hub.", "Ajoutez d'abord une clé et l'adresse du hub, puis testez de nouveau.", "À propos", "Tailscale relie vos propres appareils en un réseau privé. L'unité lui demande une route vers votre hub seulement quand elle est loin de la maison. Votre voix, vos images et vos réglages vont de l'unité à votre hub et nulle part ailleurs.", "Lire le guide complet",
        "À propos", "Code source et docs", "Open source : libre à lire, utiliser et modifier.", "Version de l'hôte", "Licence", "Docs d'utilisation",
        "Télécommande", "Actions rapides", "Bip", "Faire clignoter", "Trouver mon robot", "Arrêter la recherche", "Dire quelque chose", "Mots à dire", "Parler", "Pavé de la tête", "Centrer",
        "Regarder autour", "Dire oui", "Dire non", "Danser", "Danser maintenant", "Arrêter la danse", "Lancer un jeu", "Jouer", "Prendre une photo", "Nécessite la version avec caméra", "La photo que l'unité vient de prendre",
        "Sourdine", "Réactiver le son", "Redémarrer", "Fait.", "Cette unité est hors ligne. Allumez-la et approchez-la du routeur, puis réessayez.", "Limites de la tête : gauche et droite 128 degrés, haut et bas de 5 à 85 degrés.", "En cours...", "Le robot bipe et clignote jusqu'à ce que vous l'arrêtiez.",
    ),
    "de": (
        "Erstellen Sie in Ihrer Tailscale-Verwaltung einen Authentifizierungsschlüssel: einmalig und mit Tag.", "Tailscale-Schlüsselseite öffnen", "Fügen Sie den Schlüssel hier ein und senden Sie ihn an das Gerät.", "Geben Sie die Tailscale-Adresse Ihres Heim-Hubs ein und speichern Sie sie.", "Was passiert", "Das Gerät tritt Ihrem Tailscale-Netzwerk nur bei, wenn es den Hub nicht erreicht.", "Zu Hause startet es nie.", "Der Schlüssel wird nach dem Beitritt vom Gerät gelöscht.", "Nichts geht an MaiPai.", "Adresse speichern",
        "Aus", "Wartet", "Verbindet", "Verbunden", "Problem",
        "Tailscale-Adresse des Geräts", "Die Hub-Verbindung läuft über", "Ihr Heimnetz", "Tailscale", "Letztes Problem",
        "Der Schlüssel wurde nicht akzeptiert. Erstellen Sie einen neuen Einmalschlüssel und fügen Sie ihn erneut ein.", "Die Hub-Adresse ist ungültig. Verwenden Sie die Form 100.x.x.x und speichern Sie erneut.", "Die Firmware dieses Geräts wurde ohne Tailscale gebaut. Aktualisieren Sie sie und versuchen Sie es erneut.", "Das Gerät tritt gerade bei. Starten Sie es neu und vergessen Sie dann den Schlüssel.", "Dem Gerät fehlt freier Arbeitsplatz. Versuchen Sie es in einer Minute erneut.",
        "Testen", "Es funktioniert. Das Gerät ist in Ihrem Tailscale-Netzwerk und die Hub-Verbindung nutzt es.", "Bereit. Das Gerät tritt Tailscale nur bei, wenn es den Hub nicht erreicht.", "Fügen Sie zuerst einen Schlüssel und die Hub-Adresse hinzu und testen Sie erneut.", "Über das hier", "Tailscale verbindet Ihre eigenen Geräte zu einem privaten Netzwerk. Das Gerät fragt es nur nach einer Route zu Ihrem Hub, wenn es nicht zu Hause ist. Ihre Stimme, Bilder und Einstellungen gehen vom Gerät zu Ihrem Hub und nirgendwohin sonst.", "Die ganze Anleitung lesen",
        "Über", "Quellcode und Doku", "Open Source: frei zu lesen, zu nutzen und zu ändern.", "Host-Version", "Lizenz", "Benutzerdoku",
        "Fernbedienung", "Schnellaktionen", "Piepton", "Lichter blinken", "Meinen Roboter finden", "Suche beenden", "Etwas sagen", "Zu sagende Worte", "Sprechen", "Kopf-Pad", "Mitte",
        "Umsehen", "Ja nicken", "Nein schütteln", "Tanzen", "Jetzt tanzen", "Tanz stoppen", "Spiel starten", "Spielen", "Foto aufnehmen", "Braucht die Kamera-Version", "Das Foto, das das Gerät gerade gemacht hat",
        "Stumm", "Ton an", "Neustart", "Erledigt.", "Dieses Gerät ist offline. Schalten Sie es ein und bringen Sie es in die Nähe des Routers, dann versuchen Sie es erneut.", "Kopfgrenzen: links und rechts 128 Grad, oben und unten 5 bis 85 Grad.", "Läuft...", "Der Roboter piept und blinkt, bis Sie ihn stoppen.",
    ),
    "pt": (
        "No console de administração do Tailscale, crie uma chave de autenticação: de uso único e com etiqueta.", "Abrir a página de chaves do Tailscale", "Cole a chave aqui e envie para a unidade.", "Digite o endereço Tailscale do seu hub em casa e salve.", "O que acontece", "A unidade entra na sua rede Tailscale só quando não consegue falar com o hub.", "Em casa ela nunca inicia.", "A chave é apagada da unidade depois que ela entra.", "Nada vai para a MaiPai.", "Salvar o endereço",
        "Desligado", "Aguardando", "Conectando", "Conectada", "Problema",
        "Endereço Tailscale da unidade", "A conexão com o hub passa por", "Sua rede de casa", "Tailscale", "Último problema",
        "A chave não foi aceita. Crie uma nova chave de uso único e cole de novo.", "O endereço do hub não é válido. Use a forma 100.x.x.x e salve de novo.", "O firmware desta unidade foi criado sem Tailscale. Atualize o firmware e tente de novo.", "A unidade está entrando agora. Reinicie-a e depois esqueça a chave.", "A unidade está sem espaço livre de trabalho. Tente de novo em um minuto.",
        "Testar", "Funcionando. A unidade está na sua rede Tailscale e a conexão com o hub a usa.", "Pronta. A unidade entra no Tailscale só se não conseguir falar com o hub.", "Adicione primeiro uma chave e o endereço do hub, e teste de novo.", "Sobre isto", "O Tailscale junta seus próprios aparelhos em uma rede privada. A unidade pede a ele um caminho até o seu hub só quando está fora de casa. Sua voz, imagens e configurações vão da unidade ao seu hub e a nenhum outro lugar.", "Ler o guia completo",
        "Sobre", "Código-fonte e documentação", "Código aberto: livre para ler, usar e mudar.", "Versão do computador", "Licença", "Documentação de uso",
        "Remoto", "Ações rápidas", "Bipe", "Piscar luzes", "Achar meu robô", "Parar de procurar", "Dizer algo", "Palavras para dizer", "Falar", "Painel da cabeça", "Centralizar",
        "Olhar em volta", "Dizer sim", "Dizer não", "Dançar", "Dançar agora", "Parar a dança", "Iniciar um jogo", "Jogar", "Tirar uma foto", "Precisa da versão com câmera", "A foto que a unidade acabou de tirar",
        "Silenciar", "Reativar o som", "Reiniciar", "Pronto.", "Esta unidade está offline. Ligue-a e aproxime-a do roteador, e tente de novo.", "Limites da cabeça: esquerda e direita 128 graus, cima e baixo de 5 a 85 graus.", "Trabalhando...", "O robô apita e pisca até você parar.",
    ),
    "it": (
        "Nella console di amministrazione di Tailscale crea una chiave di autenticazione: monouso e con etichetta.", "Apri la pagina delle chiavi di Tailscale", "Incolla qui la chiave e inviala all'unità.", "Scrivi l'indirizzo Tailscale del tuo hub di casa e salvalo.", "Cosa succede", "L'unità entra nella tua rete Tailscale solo quando non raggiunge l'hub.", "A casa non parte mai.", "La chiave viene cancellata dall'unità dopo l'ingresso.", "Nulla va a MaiPai.", "Salva l'indirizzo",
        "Spento", "In attesa", "Connessione", "Connessa", "Problema",
        "Indirizzo Tailscale dell'unità", "Il collegamento con l'hub passa per", "La tua rete di casa", "Tailscale", "Ultimo problema",
        "La chiave non è stata accettata. Crea una nuova chiave monouso e incollala di nuovo.", "L'indirizzo dell'hub non è valido. Usa la forma 100.x.x.x e salva di nuovo.", "Il firmware di questa unità è stato creato senza Tailscale. Aggiornalo e riprova.", "L'unità si sta collegando adesso. Riavviala, poi dimentica la chiave.", "All'unità manca spazio libero di lavoro. Riprova tra un minuto.",
        "Prova", "Funziona. L'unità è nella tua rete Tailscale e il collegamento con l'hub la usa.", "Pronta. L'unità entra in Tailscale solo se non raggiunge l'hub.", "Aggiungi prima una chiave e l'indirizzo dell'hub, poi prova di nuovo.", "Informazioni", "Tailscale unisce i tuoi dispositivi in una rete privata. L'unità gli chiede una via verso il tuo hub solo quando è lontana da casa. Voce, immagini e impostazioni vanno dall'unità al tuo hub e da nessun'altra parte.", "Leggi la guida completa",
        "Informazioni", "Codice sorgente e documenti", "Open source: libero di leggere, usare e modificare.", "Versione dell'host", "Licenza", "Documenti d'uso",
        "Telecomando", "Azioni rapide", "Bip", "Lampeggia luci", "Trova il mio robot", "Smetti di cercare", "Di' qualcosa", "Parole da dire", "Parla", "Pad della testa", "Centra",
        "Guarda intorno", "Di' sì col capo", "Di' no col capo", "Balla", "Balla ora", "Ferma il ballo", "Avvia un gioco", "Gioca", "Scatta una foto", "Serve la versione con fotocamera", "La foto appena scattata dall'unità",
        "Silenzia", "Riattiva audio", "Riavvia", "Fatto.", "Questa unità è offline. Accendila e avvicinala al router, poi riprova.", "Limiti della testa: sinistra e destra 128 gradi, su e giù da 5 a 85 gradi.", "In corso...", "Il robot suona e lampeggia finché non lo fermi.",
    ),
}  # fmt: skip

for _code, _words in _TEXT3.items():
    CATALOGS[_code].update({f"settings.ui.{k}": v for k, v in zip(KEYS3, _words, strict=True)})

# The Tailscale wording replaces the old "travel key" and "private network" labels, and "Device-Id" becomes plain.
OVERRIDES: dict[str, dict[str, str]] = {
    "en": {"settings.ui.units.travel": "Use it anywhere (Tailscale)", "settings.ui.units.travel_help": "Take the robot to any other Wi-Fi and it reaches your home hub through your own Tailscale network.", "settings.ui.units.travel_key": "Tailscale auth key (tskey-...)", "settings.ui.units.travel_send": "Send the key", "settings.ui.units.travel_forget": "Forget the key", "settings.ui.units.travel_hidden": "The key goes straight to the unit. It is never shown or kept on this computer.", "settings.ui.net.private": "Use it anywhere (Tailscale)", "settings.ui.net.private_on": "Use Tailscale when away from home", "settings.ui.net.hub_addr": "Home hub's Tailscale address (100.x.x.x)", "settings.device_id": "Unit ID"},
    "es": {"settings.ui.units.travel": "Úsalo en cualquier sitio (Tailscale)", "settings.ui.units.travel_help": "Lleva el robot a otro Wi-Fi y llega a tu hub en casa por tu propia red de Tailscale.", "settings.ui.units.travel_key": "Clave de autenticación de Tailscale (tskey-...)", "settings.ui.units.travel_send": "Enviar la clave", "settings.ui.units.travel_forget": "Olvidar la clave", "settings.ui.units.travel_hidden": "La clave va directa a la unidad. Nunca se muestra ni se guarda en este ordenador.", "settings.ui.net.private": "Úsalo en cualquier sitio (Tailscale)", "settings.ui.net.private_on": "Usar Tailscale fuera de casa", "settings.ui.net.hub_addr": "Dirección de Tailscale del hub en casa (100.x.x.x)", "settings.device_id": "ID de la unidad"},
    "fr": {"settings.ui.units.travel": "Utilisez-le partout (Tailscale)", "settings.ui.units.travel_help": "Emportez le robot sur un autre Wi-Fi et il joint votre hub à la maison par votre propre réseau Tailscale.", "settings.ui.units.travel_key": "Clé d'authentification Tailscale (tskey-...)", "settings.ui.units.travel_send": "Envoyer la clé", "settings.ui.units.travel_forget": "Oublier la clé", "settings.ui.units.travel_hidden": "La clé va directement à l'unité. Elle n'est jamais affichée ni conservée sur cet ordinateur.", "settings.ui.net.private": "Utilisez-le partout (Tailscale)", "settings.ui.net.private_on": "Utiliser Tailscale hors de la maison", "settings.ui.net.hub_addr": "Adresse Tailscale du hub à la maison (100.x.x.x)", "settings.device_id": "ID de l'unité"},
    "de": {"settings.ui.units.travel": "Überall nutzen (Tailscale)", "settings.ui.units.travel_help": "Nehmen Sie den Roboter in ein anderes WLAN mit, und er erreicht Ihren Heim-Hub über Ihr eigenes Tailscale-Netzwerk.", "settings.ui.units.travel_key": "Tailscale-Authentifizierungsschlüssel (tskey-...)", "settings.ui.units.travel_send": "Schlüssel senden", "settings.ui.units.travel_forget": "Schlüssel vergessen", "settings.ui.units.travel_hidden": "Der Schlüssel geht direkt an das Gerät. Er wird nie angezeigt oder auf diesem Computer gespeichert.", "settings.ui.net.private": "Überall nutzen (Tailscale)", "settings.ui.net.private_on": "Tailscale außer Haus nutzen", "settings.ui.net.hub_addr": "Tailscale-Adresse des Heim-Hubs (100.x.x.x)", "settings.device_id": "Geräte-ID"},
    "pt": {"settings.ui.units.travel": "Use em qualquer lugar (Tailscale)", "settings.ui.units.travel_help": "Leve o robô para outro Wi-Fi e ele chega ao seu hub em casa pela sua própria rede Tailscale.", "settings.ui.units.travel_key": "Chave de autenticação do Tailscale (tskey-...)", "settings.ui.units.travel_send": "Enviar a chave", "settings.ui.units.travel_forget": "Esquecer a chave", "settings.ui.units.travel_hidden": "A chave vai direto para a unidade. Nunca é mostrada nem guardada neste computador.", "settings.ui.net.private": "Use em qualquer lugar (Tailscale)", "settings.ui.net.private_on": "Usar o Tailscale fora de casa", "settings.ui.net.hub_addr": "Endereço Tailscale do hub em casa (100.x.x.x)", "settings.device_id": "ID da unidade"},
    "it": {"settings.ui.units.travel": "Usalo ovunque (Tailscale)", "settings.ui.units.travel_help": "Porta il robot su un altro Wi-Fi e raggiunge il tuo hub di casa tramite la tua rete Tailscale.", "settings.ui.units.travel_key": "Chiave di autenticazione Tailscale (tskey-...)", "settings.ui.units.travel_send": "Invia la chiave", "settings.ui.units.travel_forget": "Dimentica la chiave", "settings.ui.units.travel_hidden": "La chiave va dritta all'unità. Non viene mai mostrata né conservata su questo computer.", "settings.ui.net.private": "Usalo ovunque (Tailscale)", "settings.ui.net.private_on": "Usa Tailscale fuori casa", "settings.ui.net.hub_addr": "Indirizzo Tailscale dell'hub di casa (100.x.x.x)", "settings.device_id": "ID dell'unità"},
}
for _code, _over in OVERRIDES.items():
    CATALOGS[_code].update(_over)
