"""Default Daily Prophet editions, using newly generated AI assets and original format."""
import os
from .models import NewspaperEdition, Story, StoryPriority


def get_hogwarts_legacy_edition(base_dir: str = ".") -> NewspaperEdition:
    """Returns the Hogwarts Legacy issue from Sample 1 (Professor Fig, Sharp, Tomes & Scrolls)."""
    lib_char = os.path.join(base_dir, "assets", "library", "characters")
    lib_loc = os.path.join(base_dir, "assets", "library", "locations")

    fig_cutout = os.path.join(lib_char, "professor_fig_cutout.png")
    if not os.path.isfile(fig_cutout):
        fig_cutout = os.path.join(lib_char, "professor_fig.png")

    sharp_cutout = os.path.join(lib_char, "professor_sharp_cutout.png")
    if not os.path.isfile(sharp_cutout):
        sharp_cutout = os.path.join(lib_char, "professor_sharp.png")

    office_img = os.path.join(lib_loc, "headmasters_office.png")
    tomes_img = os.path.join(lib_loc, "tomes_and_scrolls.png")
    village_img = os.path.join(lib_loc, "hogsmeade_village.png")

    stories = [
        Story(
            id="legacy-fig-beans",
            headline="MR. FIGS BEANS STOLEN! HELP NEEDED FROM RAVENCLAW",
            subheadline="Mischief is afoot in Hogsmeade! Prized magical beans go missing from office.",
            author="Josh Moonglow, Ravenclaw",
            priority=StoryPriority.COVER.value,
            location_tag="HOGSMEADE & CASTLE",
            body=(
                "Mischief is afoot in Hogsmeade! Mr. Fig's prized beans have gone missing from his private chambers!\n\n"
                "The beloved professor is asking for the swift return of his beans, which were recently stolen from his office. "
                "If you have seen them or have any information about their sudden disappearance, please contact Josh Moonglow of Ravenclaw.\n\n"
                "Let's help get Mr. Fig's beans back where they belong! Castle prefects are on alert."
            ),
            image_path=os.path.abspath(fig_cutout) if os.path.isfile(fig_cutout) else "",
            inline_image_path=os.path.abspath(fig_cutout) if os.path.isfile(fig_cutout) else "",
            inline_image_align="left",
            character_tag="Professor Fig",
            image_caption="Professor Fig in his study, appealing for information regarding his missing beans.",
            box_style="standard",
        ),
        Story(
            id="legacy-headmaster-office",
            headline="SUMMONED TO THE HEADMASTER'S OFFICE",
            subheadline="WHAT COULD IT MEAN? WHISPERS AROUND THE CASTLE",
            author="Castle Inquirer",
            priority=StoryPriority.MAJOR.value,
            location_tag="HEADMASTER'S TOWER",
            body=(
                "Reports around the castle suggest that several students have recently been called to the Headmaster's office. "
                "What about? Only they know.\n\n"
                "It seems to be a growing trend among those who have graduated but have chosen to remain at Hogwarts to tutor and help "
                "our newest students. Could this be recognition for their dedication? Possible new responsibilities? Rewards?\n\n"
                "Whatever the reason, we extend a heartfelt thank you to all of our 7+ year students who continue to stick around, "
                "support the castle, and help guide the next generation."
            ),
            image_path=os.path.abspath(office_img) if os.path.isfile(office_img) else "",
            image_caption="The Headmaster's high tower office overlooking the foggy Scottish highlands.",
            pull_quote='"Your time, knowledge, and presence make Hogwarts a brighter place." — Castle Dispatch',
            box_style="speech_quote",
        ),
        Story(
            id="legacy-potions-sharp",
            headline="POTIONS CLASS TROUBLE: EXPERIMENTS LEAD TO WARNINGS",
            subheadline="Students getting creative outside lesson plans; Professor Sharp is not amused.",
            author="Dungeon Observer",
            priority=StoryPriority.COLUMN.value,
            location_tag="POTIONS DUNGEON",
            body=(
                "Students in Potions class have been getting a bit too creative lately, with reports of unsanctioned experiments "
                "taking place outside of the curriculum.\n\n"
                "Professor Sharp is not amused. Students are reminded to follow instructions, respect the classroom, and leave "
                "unauthorized experiments for another time. Potions can be dangerous, and Professor Sharp will not tolerate reckless brewing."
            ),
            image_path=os.path.abspath(sharp_cutout) if os.path.isfile(sharp_cutout) else "",
            inline_image_path=os.path.abspath(sharp_cutout) if os.path.isfile(sharp_cutout) else "",
            inline_image_align="right",
            character_tag="Professor Sharp",
            image_caption="Professor Sharp inspecting cauldrons in the subterranean dungeon.",
            box_style="standard",
        ),
        Story(
            id="legacy-tomes-scrolls",
            headline="TOMES AND SCROLLS IS OPEN IN HOGSMEADE",
            subheadline="Thomas Brown offers Room of Requirement spellcrafts & furnishings.",
            author="Hogsmeade Trade Gazette",
            priority=StoryPriority.COLUMN.value,
            location_tag="HOGSMEADE VILLAGE",
            body=(
                "Tomes and Scrolls is now open in Hogsmeade! Thomas Brown sells every Room of Requirement spellcraft for those "
                "looking to furnish their spaces.\n\n"
                "SELL YOUR WARES: Pippin's Potions and Tomes and Scrolls now feature a convenient Sell tab. Click an item, then click again "
                "to exchange for Galleons and Sickles. School robes and active gear cannot be sold."
            ),
            image_path=os.path.abspath(tomes_img) if os.path.isfile(tomes_img) else "",
            image_caption="Thomas Brown's Tomes and Scrolls shop in high street Hogsmeade.",
            box_style="standard",
        ),
        Story(
            id="legacy-holiday-decorations",
            headline="SEASONAL DECORATIONS ENCHANT THE CASTLE",
            subheadline="Festive pumpkins and enchanted candles light the village and courtyards.",
            author="Hogwarts Social Column",
            priority=StoryPriority.COLUMN.value,
            location_tag="HOGWARTS & GROUNDS",
            body=(
                "The castle and Hogsmeade have been newly decorated for the turning season!\n\n"
                "Keep an eye out as the weather cools and enchanting decorations appear throughout the courtyards, common halls, and "
                "cobblestone streets, bringing an extra spark of wonder to our community."
            ),
            image_path=os.path.abspath(village_img) if os.path.isfile(village_img) else "",
            image_caption="Twilight over the lantern-lit rooftops of Hogsmeade village.",
            box_style="standard",
        ),
    ]

    return NewspaperEdition(
        paper_title="The Daily Prophet",
        tagline="THE WIZARDING WORLD'S MOST TRUSTED SOURCE OF NEWS",
        topic_bar="HOGWARTS ★ HOGSMEADE ★ MINISTRY ★ MAGICAL CREATURES ★ COMMUNITY",
        edition_date="22 OCTOBER",
        edition_day="THURSDAY",
        issue_number="NO. 28,491",
        edition_label="HOGWARTS EDITION",
        price="1 KNUT",
        weather="Mild and Misty with Chance of Spells",
        top_left_banner="WEATHER: Castle Weather - Mild and Misty",
        top_right_banner="COMMUNITY: The Wizarding World's Most Trusted News",
        footer_slogan="GOOD NEWS, BRIGHTER DAYS, A MORE MAGICAL TOMORROW",
        theme="original_prophet",
        border_style="ornate_engraved",
        magical_motion=True,
        quote_author="PROFESSOR SHARP",
        quote_text="Curiosity often leads to discovery, but wisdom knows which doors should remain closed.",
        lore_title_1="THIS DAY IN WIZARDING HISTORY",
        lore_body_1="October 22, 1707: The first recorded official appearance of a Boggart was documented by the Department of Magical Creatures, establishing essential safety guidelines for classrooms and populated areas.",
        lore_title_2="DID YOU KNOW? HOGWARTS LORE",
        lore_body_2="The Lumos charm was first recorded in the 16th century and remains one of the most widely used spells among witches and wizards, illuminating the darkest passages of Hogwarts.",
        stories=stories,
    )


def get_original_hogwarts_edition(base_dir: str = ".") -> NewspaperEdition:
    """Returns the Hogwarts Original Issue with generated AI artwork."""
    lib_dir = os.path.join(base_dir, "assets", "library")
    char_dir = os.path.join(lib_dir, "characters")
    loc_dir = os.path.join(lib_dir, "locations")
    artifact_dir = os.path.join(lib_dir, "creatures_and_artifacts")

    castle_img = os.path.join(loc_dir, "hogwarts_castle_twilight.png")
    houses_img = os.path.join(artifact_dir, "four_houses_heraldic.png")
    owl_img = os.path.join(artifact_dir, "owl_post_cutout.png")
    discord_img = os.path.join(loc_dir, "muggle_studies_terminal.png")
    quidditch_img = os.path.join(loc_dir, "quidditch_pitch_flying.png")
    potions_img = os.path.join(loc_dir, "potions_cauldron_accident.png")
    scrolls_img = os.path.join(loc_dir, "tomes_and_scrolls.png")
    office_img = os.path.join(loc_dir, "headmasters_office.png")

    stories = [
        # 1. COVER HERO STORY
        Story(
            id="hogwarts-hero",
            headline="HOGWARTS UNDERGOES MYSTERIOUS TRANSFORMATION!",
            subheadline="Castle corridors rearranged overnight! Ministry officials deny involvement.",
            author="Special Correspondent",
            priority=StoryPriority.COVER.value,
            location_tag="HOGWARTS, SCOTLAND",
            body=(
                "Students and faculty awoke this morning to discover that the halls of Hogwarts School of Witchcraft "
                "and Wizardry had undergone a rather extraordinary transformation!\n\n"
                "New chambers have appeared, corridors have been reorganized, and previously overlooked gathering spaces "
                "have been opened to the student body.\n\n"
                "Hogwarts Administration confirms these changes are part of an extensive effort to improve castle life. "
                "Perhaps most excitingly, the four House Common Rooms are now accessible to their respective students!"
            ),
            image_path=castle_img,
            image_caption="Hogwarts Castle at twilight, where enchanted architectural shifts were observed at dawn.",
            box_style="standard",
        ),
        # 2. UPPER RIGHT FEATURE - THE FOUR HOUSES
        Story(
            id="four-houses-feature",
            headline="THE FOUR HOUSES AWAIT YOU!",
            subheadline="GRYFFINDOR Tower • SLYTHERIN Dungeon • RAVENCLAW Tower • HUFFLEPUFF Basement",
            author="Hogwarts Sorting Ceremony",
            priority=StoryPriority.MAJOR.value,
            body=(
                "Students must first visit the Sorting Ceremony to officially declare their House allegiance.\n\n"
                "Each Common Room offers distinct enchantments, ancient house pride, and dedicated gathering halls."
            ),
            image_path=houses_img,
            image_caption="Official heraldic banners of the four Hogwarts founders.",
            pull_quote='"One student, one House! I shall not tolerate indecisive witches and wizards attempting to occupy four Common Rooms at once!" — The Sorting Hat',
            box_style="speech_quote",
        ),
        # 3. MIDDLE LEFT - OWL POST
        Story(
            id="owl-post-story",
            headline="OWL POST OFFICE ANNOUNCES NEW DELIVERY SYSTEM!",
            subheadline="Unnecessary Howlers expected to decline dramatically.",
            author="Owleries Superintendent",
            priority=StoryPriority.COLUMN.value,
            body=(
                "In a revolutionary advancement in magical communication, Hogwarts Administration has introduced a new system "
                "allowing students to choose which official notices they receive.\n\n"
                "Students may now register for specific announcements, including castle maintenance, development news, community notices, "
                "school events, and roleplay activities.\n\n"
                "The system was reportedly developed following numerous complaints about excessive owl deliveries."
            ),
            image_path=owl_img,
            image_caption="Hogwarts Barn Owl delivering official correspondence.",
            pull_quote='"If I have to deliver one more announcement about a corridor being closed, I\'m transferring to Beauxbatons." — An exhausted barn owl',
            box_style="speech_quote",
        ),
        # 4. MIDDLE CENTER - MUGGLE STUDIES DISCORD
        Story(
            id="muggle-discord-story",
            headline="MUGGLE STUDIES: THE MYSTERY OF THE 'DISCORD'",
            subheadline="Professor baffled by peculiar Muggle communication invention.",
            author="Department of Muggle Studies",
            priority=StoryPriority.COLUMN.value,
            body=(
                "Hogwarts' Muggle Studies department has reportedly begun investigating a curious invention known as Discord.\n\n"
                "According to preliminary findings, this extraordinary device allows Muggles to communicate instantly across enormous "
                "distances without the assistance of owls, Floo Powder, or enchanted mirrors.\n\n"
                "Even more astonishing, users apparently communicate using tiny pictures called emojis. One professor was particularly "
                "disturbed to discover that a simple green snake 🐍 could communicate one's House allegiance.\n\n"
                "'Extraordinary! They have managed to invent a form of magical correspondence without possessing an ounce of magic!' "
                "The Department of Magical Accidents and Catastrophes has advised students against attempting to cast Reparo on malfunctioning Muggle computers."
            ),
            image_path=discord_img,
            image_caption="Ancient tome and enchanted Muggle terminal under scholarly investigation.",
            box_style="standard",
        ),
        # 5. MIDDLE RIGHT 1 - QUIDDITCH FLYING SATHEL
        Story(
            id="quidditch-story",
            headline="QUIDDITCH PRACTICE - INTERRUPTED BY UNIDENTIFIED FLYING OBJECT",
            subheadline="Enchanted schoolbag evades Chasers above the pitch",
            author="Sports Desk",
            priority=StoryPriority.COLUMN.value,
            body=(
                "An afternoon training session was abruptly interrupted when students reported a mysterious object soaring across "
                "the Quidditch pitch.\n\n"
                "Witnesses initially believed the object to be a rogue Bludger. Further investigation revealed it was a student's enchanted "
                "schoolbag, apparently attempting to escape an unfinished Potions assignment.\n\n"
                "The bag was eventually recovered near the Owlery. No injuries were reported, although three essays remain missing."
            ),
            image_path=quidditch_img,
            image_caption="The rogue schoolbag evading flying broomsticks.",
            box_style="standard",
        ),
        # 6. MIDDLE RIGHT 2 - POTIONS DISASTER
        Story(
            id="potions-story",
            headline="POTIONS CLASS ENDS IN UNEXPECTED DISASTER",
            subheadline="Moonstone confused with ordinary baking flour",
            author="Dungeon Observer",
            priority=StoryPriority.COLUMN.value,
            body=(
                "A routine brewing exercise took an unfortunate turn yesterday when an unidentified student allegedly confused "
                "powdered moonstone with ordinary baking flour.\n\n"
                "The resulting potion produced a thick cloud of violet smoke, caused several cauldrons to sing in harmony, and "
                "temporarily turned a classroom chair into a rather irritated goose. The professor has declined to comment. "
                "The goose has reportedly requested a transfer to Hufflepuff."
            ),
            image_path=potions_img,
            image_caption="Singing violet cauldron in the Potions dungeon.",
            box_style="standard",
        ),
        # 7. BOTTOM LEFT - HOGWARTS HISTORY
        Story(
            id="history-snippet",
            headline="DID YOU KNOW? HOGWARTS HISTORY",
            subheadline="Ancient lore and secret passages",
            author="School Archivist",
            priority=StoryPriority.SNIPPET.value,
            body=(
                "★ The Founders: Hogwarts was established over a thousand years ago by Godric Gryffindor, Salazar Slytherin, "
                "Rowena Ravenclaw, and Helga Hufflepuff.\n\n"
                "★ The Room of Requirement: A mysterious chamber that appears only when someone has genuine need of it.\n\n"
                "★ Hufflepuff Hospitality: The Hufflepuff Common Room is located near the kitchens, making it particularly convenient "
                "for students with a fondness for midnight snacks.\n\n"
                "★ Ravenclaw's Entrance: Unlike the other Houses, Ravenclaw students traditionally gain entry to their Common Room "
                "by answering an esoteric riddle."
            ),
            image_path=scrolls_img,
            box_style="ornate_box",
        ),
        # 8. BOTTOM CENTER - WIZARDING FORECAST
        Story(
            id="forecast-snippet",
            headline="THIS WEEK'S WIZARDING FORECAST",
            subheadline="Highlands Atmospheric Divination",
            author="Astronomy Tower Observatory",
            priority=StoryPriority.SNIPPET.value,
            body=(
                "☁️ Hogwarts Castle: Cloudy skies, scattered enchantments, and a 70% chance of students being late to class.\n\n"
                "🌲 Forbidden Forest: Dense fog, suspicious noises, and absolutely no reason to investigate after sunset.\n\n"
                "🎃 Great Hall: Warm atmosphere with occasional showers of pumpkin juice.\n\n"
                "🐍 Slytherin Common Room: Cool, mysterious, and an exceptionally high concentration of ambition."
            ),
            box_style="parchment_scroll",
        ),
        # 9. BOTTOM RIGHT - FINAL WORD FROM THE EDITOR
        Story(
            id="editor-word-snippet",
            headline="A FINAL WORD FROM THE EDITOR",
            subheadline="Until tomorrow, keep your wands ready!",
            author="The Daily Prophet — Castle Life RP",
            priority=StoryPriority.SNIPPET.value,
            body=(
                "As Hogwarts enters a new chapter, students are encouraged to explore the castle, embrace their House pride, "
                "and participate in the growing magical community.\n\n"
                "The greatest magic at Hogwarts is not found in a wand, a potion, or an ancient spell. It is found in the stories "
                "we create together.\n\n"
                "Until tomorrow, keep your wands ready and your owls well-fed!"
            ),
            image_path=office_img,
            box_style="wanted_poster",
        ),
    ]

    return NewspaperEdition(
        paper_title="The Daily Prophet",
        tagline="THE WIZARDING WORLD'S MOST ENCHANTING NEWSPAPER",
        topic_bar="NEWS ★ SPELLS ★ EVENTS ★ RUMOURS ★ HOGWARTS ★ THE MINISTRY",
        edition_date="19 OCTOBER 1890",
        edition_day="MONDAY",
        issue_number="EDITION No. 317",
        edition_label="HOGWARTS EDITION",
        price="ONE KNUT",
        top_left_banner="EDITION No. 317 • MONDAY • 19 OCTOBER 1890",
        top_right_banner="HOGWARTS EDITION • PRICE: ONE KNUT",
        breaking_banner="",
        footer_slogan="GOOD NEWS, BRIGHTER DAYS, A MORE MAGICAL TOMORROW",
        theme="original_prophet",
        magical_motion=True,
        stories=stories,
    )


def get_azkaban_edition(base_dir: str = ".") -> NewspaperEdition:
    """Returns the Azkaban / Sirius Black breakout edition."""
    lib_dir = os.path.join(base_dir, "assets", "library")
    char_dir = os.path.join(lib_dir, "characters")
    loc_dir = os.path.join(lib_dir, "locations")
    artifact_dir = os.path.join(lib_dir, "creatures_and_artifacts")

    sirius_img = os.path.join(char_dir, "dark_wizard_encounter_cutout.png")
    if not os.path.isfile(sirius_img):
        sirius_img = os.path.join(char_dir, "dark_wizard_encounter.png")
    triwizard_img = os.path.join(artifact_dir, "four_houses_heraldic.png")
    quidditch_img = os.path.join(loc_dir, "quidditch_pitch_flying.png")
    ministry_img = os.path.join(artifact_dir, "slytherin_crest.png")

    stories = [
        Story(
            id="azkaban-cover",
            headline="MASS BREAKOUT FROM AZKABAN!",
            subheadline="MINISTRY CONFIRMS CONVICTED MASS-MURDERER SIRIUS BLACK HAS ESCAPED DEMENTOR FORTRESS",
            author="By Rita Skeeter, Special Inquirer",
            priority=StoryPriority.COVER.value,
            location_tag="LONDON",
            body=(
                "In an unprecedented breach of security that has left the Department of Magical Law Enforcement reeling, "
                "Sirius Black, notorious lieutenant of You-Know-Who, has escaped from Azkaban fortress under circumstances "
                "no auror can fathom.\n\n"
                "Minister for Magic Cornelius Fudge addressed an emergency session of the Wizengamot at dawn: 'We are taking "
                "unprecedented countermeasures. Azkaban has stood impregnable for over three centuries; how Black managed to slip "
                "past hundreds of Dementors is the subject of high-level inquiry. We urge calm, yet advise absolute vigilance.'\n\n"
                "Citizens are warned in the strongest terms not to approach Black. Witnesses characterize him as erratic, emaciated, "
                "and capable of devastating wandless hexes. Patrols of Azkaban Dementors have been dispatched across major wizarding "
                "settlements, including Diagon Alley and Hogsmeade.\n\n"
                "Headmaster Albus Dumbledore has reinforced defensive enchantments around Hogwarts School of Witchcraft and Wizardry, "
                "affirming that student safety remains paramount."
            ),
            image_path=os.path.abspath(sirius_img) if os.path.isfile(sirius_img) else "",
            image_caption="Sirius Black, photographed during his Azkaban internment. Considered armed and extraordinarily dangerous.",
            pull_quote="'He could be anywhere, disguised or lurking in shadow. We must remain on highest guard.'",
            box_style="standard",
        ),
        Story(
            id="triwizard-major",
            headline="TRIWIZARD TOURNAMENT REVIVED AT HOGWARTS",
            subheadline="Champions from Three European Academies to Compete for Eternal Glory and 1,000 Galleons",
            author="By Elphias Doge, Wizarding Affairs Correspondent",
            priority=StoryPriority.MAJOR.value,
            location_tag="SCOTLAND",
            body=(
                "Following months of diplomatic negotiations between the British, French, and Scandinavian Ministries, the fabled "
                "Triwizard Tournament has been formally resurrected after a two-hundred-year hiatus.\n\n"
                "Delegations from Beauxbatons Academy and the Durmstrang Institute arrived on grounds yesterday via flying carriage "
                "and submerged galleon respectively. The impartial selection of three champions will be arbitrated solely by the ancient "
                "Goblet of Fire.\n\n"
                "To mitigate historical perils, an Age Line drawn by Dumbledore restricts applicants to wizards seventeen and older."
            ),
            image_path=os.path.abspath(triwizard_img) if os.path.isfile(triwizard_img) else "",
            image_caption="The fabled Triwizard Cup, currently enshrined in the Hogwarts Great Hall.",
            box_style="standard",
        ),
        Story(
            id="quidditch-column",
            headline="QUIDDITCH WORLD CUP: IRELAND TRIUMPHS",
            subheadline="Krum Catches the Golden Snitch, but Relentless Irish Chasers Clinch 170 to 160 Victory",
            author="By Kennilworthy Whisp",
            priority=StoryPriority.COLUMN.value,
            location_tag="DARTMOOR",
            body=(
                "In one of the most breathless finals recorded in Quidditch annals, the Irish national squad snatched victory before "
                "one hundred thousand roaring spectators.\n\n"
                "Bulgarian prodigy Viktor Krum pulled off a magnificent Wronski Feint and seized the golden snitch, but Troy, Mullet, "
                "and Moran's brilliant passing maneuvers built an insurmountable points barrier."
            ),
            image_path=os.path.abspath(quidditch_img) if os.path.isfile(quidditch_img) else "",
            image_caption="The Golden Snitch captured by Krum in the final seconds.",
            box_style="standard",
        ),
        Story(
            id="ministry-directive",
            headline="MINISTRY OF MAGIC DIRECTIVE #84",
            subheadline="Department of Magical Accidents and Catastrophes",
            author="Office of the Minister",
            priority=StoryPriority.SNIPPET.value,
            body=(
                "All citizens are cautioned that flying enchanted broomsticks within sight of non-magical folk (Muggles) constitutes "
                "a Class-A violation under Clause 73 of the International Statute of Wizarding Secrecy. Offending broomsticks will be "
                "impounded by the Misuse of Magic Squad."
            ),
            image_path=os.path.abspath(ministry_img) if os.path.isfile(ministry_img) else "",
            image_caption="Official Ministry Seal of Authority",
            box_style="ornate_box",
        ),
    ]

    return NewspaperEdition(
        paper_title="The Daily Prophet",
        tagline="The Wizard World's Beguiling Broadsheet of Record",
        topic_bar="NEWS ★ SPELLS ★ EVENTS ★ RUMOURS ★ HOGWARTS ★ THE MINISTRY",
        edition_date="24 OCTOBER 1994",
        edition_day="MONDAY",
        issue_number="No. 394",
        edition_label="LATE EDITION",
        price="5 KNUTS",
        top_left_banner="WEATHER: Dense fog over the Black Lake • Wand safety advisory in effect",
        top_right_banner="GRINGOTTS RATES: 1 Galleon = 17 Sickles = 493 Knuts",
        breaking_banner="SPECIAL MIDDAY EDITION • MINISTRY ON HIGH ALERT • WITCHES & WIZARDS URGED TO EXERCISE VIGILANCE",
        footer_slogan="GOOD NEWS, BRIGHTER DAYS, A MORE MAGICAL TOMORROW",
        theme="parchment",
        magical_motion=True,
        stories=stories,
    )


def get_sample_edition(base_dir: str = ".") -> NewspaperEdition:
    """Default edition loader: uses the Hogwarts Original issue as requested."""
    return get_original_hogwarts_edition(base_dir)
