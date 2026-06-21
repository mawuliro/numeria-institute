"""
Management command: seed_english_course

Creates a complete Scientific English course for university level.
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from cours.models import (
    Course, CourseModule, CourseLesson,
    LessonBlock,
    CodeExercise, MCQExercise, MCQChoice,
    FillBlankExercise, TrueFalseExercise,
)


class Command(BaseCommand):
    help = 'Seed a complete Scientific English course for university.'

    def add_arguments(self, parser):
        parser.add_argument('--draft', action='store_true', help='Create as draft.')
        parser.add_argument('--clean', action='store_true', help='Delete existing then recreate.')

    @transaction.atomic
    def handle(self, *args, **options):
        slug = 'anglais-scientifique-universite'
        status = 'draft' if options['draft'] else 'published'

        if options['clean']:
            deleted, _ = Course.objects.filter(slug=slug).delete()
            if deleted:
                self.stdout.write(self.style.WARNING(f'Deleted existing course ({deleted} rows).'))

        course, created = Course.objects.get_or_create(
            slug=slug,
            defaults={
                'title': "Scientific English for University",
                'description': (
                    "A complete course in Scientific English for university students. "
                    "Covers vocabulary, reading scientific papers, writing abstracts, "
                    "oral presentations, and academic grammar."
                ),
                'short_description': "Master Scientific English: vocabulary, papers, abstracts, presentations, grammar.",
                'category': 'autre',
                'level': 'intermediaire',
                'language': 'en',
                'price': 0,
                'is_free': True,
                'status': status,
                'estimated_hours': 35,
            },
        )
        if not created:
            self.stdout.write(self.style.WARNING(f'Course "{course.title}" already exists · updating.'))

        for module_data in COURSE_STRUCTURE:
            module = self.upsert_module(course, module_data)
            for lesson_data in module_data['lessons']:
                lesson = self.upsert_lesson(course, module, lesson_data)
                self.upsert_blocks(lesson, lesson_data['blocks'])

        self.stdout.write(self.style.SUCCESS(
            f'\n✓ Course seeded: {course.title}\n'
            f'  Modules: {CourseModule.objects.filter(course=course).count()}\n'
            f'  Lessons: {CourseLesson.objects.filter(course=course).count()}\n'
            f'  Blocks:  {LessonBlock.objects.filter(course_lesson__course=course).count()}\n'
            f'  Status:  {course.status}\n'
        ))

    def upsert_module(self, course, data):
        module, _ = CourseModule.objects.get_or_create(
            course=course, title=data['title'],
            defaults={'description': data.get('description', ''), 'order': data['order'], 'is_active': True},
        )
        return module

    def upsert_lesson(self, course, module, data):
        slug = data.get('slug') or data['title'].lower().replace(' ', '-').replace("'", '-')
        lesson, _ = CourseLesson.objects.get_or_create(
            course=course, module=module, title=data['title'],
            defaults={
                'slug': slug,
                'order': data['order'],
                'estimated_minutes': data.get('minutes', 25),
                'is_free_preview': data.get('free_preview', True),
                'is_active': True,
            },
        )
        return lesson

    def upsert_blocks(self, lesson, blocks_data):
        LessonBlock.objects.filter(course_lesson=lesson).delete()
        for idx, block_data in enumerate(blocks_data):
            self.create_block(lesson, block_data, idx)

    def create_block(self, lesson, data, idx):
        btype = data['type']
        block = LessonBlock(course_lesson=lesson, block_type=btype, order=idx)
        if btype == 'text':
            block.text_content = data['content']
            block.save()
        elif btype == 'sandbox':
            block.sandbox_title = data.get('title', 'Try it yourself')
            block.sandbox_initial_code = data.get('code', '# Write here\n')
            block.save()
        elif btype == 'mcq':
            ex = self.create_mcq(lesson, data)
            block.mcq_exercise = ex
            block.save()
        elif btype == 'code_exercise':
            ex = self.create_code_exercise(lesson, data)
            block.code_exercise = ex
            block.save()
        elif btype == 'fill_blank':
            ex = self.create_fill_blank(lesson, data)
            block.fill_blank = ex
            block.save()
        elif btype == 'true_false':
            ex = self.create_true_false(lesson, data)
            block.true_false = ex
            block.save()

    def create_mcq(self, lesson, data):
        ex = MCQExercise.objects.create(
            course_lesson=lesson, title=data['title'], question=data['question'],
            instructions=data.get('instructions', ''), difficulty=data.get('difficulty', 'easy'),
            points=data.get('points', 5), hint=data.get('hint', ''),
            explanation=data.get('explanation', ''), order=data.get('order', 0),
            allow_multiple_correct=data.get('multiple', False), shuffle_choices=True,
        )
        for i, choice in enumerate(data['choices']):
            MCQChoice.objects.create(exercise=ex, text=choice['text'], is_correct=choice['correct'],
                                     feedback=choice.get('feedback', ''), order=i)
        return ex

    def create_code_exercise(self, lesson, data):
        return CodeExercise.objects.create(
            course_lesson=lesson, title=data['title'], instructions=data.get('instructions', ''),
            difficulty=data.get('difficulty', 'easy'), points=data.get('points', 10),
            hint=data.get('hint', ''), explanation=data.get('explanation', ''), order=data.get('order', 0),
            starter_code=data.get('starter', '# Write here\n'), solution_code=data.get('solution', ''),
            expected_output=data.get('expected_output', ''), test_code=data.get('test_code', ''),
            evaluation_mode=data.get('eval_mode', 'exact'),
        )

    def create_fill_blank(self, lesson, data):
        return FillBlankExercise.objects.create(
            course_lesson=lesson, title=data['title'], instructions=data.get('instructions', ''),
            difficulty=data.get('difficulty', 'easy'), points=data.get('points', 5),
            hint=data.get('hint', ''), explanation=data.get('explanation', ''), order=data.get('order', 0),
            text_with_blanks=data['text_with_blanks'], answers=data['answers'],
            case_sensitive=data.get('case_sensitive', False),
        )

    def create_true_false(self, lesson, data):
        return TrueFalseExercise.objects.create(
            course_lesson=lesson, title=data['title'], instructions=data.get('instructions', ''),
            difficulty=data.get('difficulty', 'easy'), points=data.get('points', 6),
            hint=data.get('hint', ''), explanation=data.get('explanation', ''), order=data.get('order', 0),
            statements=data['statements'], points_per_statement=data.get('points_per_statement', 2),
        )


COURSE_STRUCTURE = [
    {
        'order': 0,
        'title': 'Scientific Vocabulary & Terminology',
        'description': 'Build the essential vocabulary for reading, writing, and speaking in science.',
        'lessons': [
            {
                'order': 0, 'title': 'Introduction to Scientific English', 'slug': 'intro-scientific-english',
                'minutes': 20, 'free_preview': True,
                'blocks': [
                    {'type': 'text', 'content': """# Introduction to Scientific English

## What is Scientific English?

**Scientific English** is a specialized register of English used in academic and professional scientific contexts. It is characterized by:

- **Precision** · exact terminology, no ambiguity
- **Objectivity** · passive voice, third-person perspective
- **Conciseness** · short, information-dense sentences
- **Formality** · no contractions (use "do not" not "don't"), no colloquialisms
- **Structure** · clear logical flow with signposting

## Why is Scientific English important?

For university students in Africa and francophone countries, mastering Scientific English is essential because:

1. **Most scientific literature** is published in English (>90% of journals)
2. **International conferences** require English presentations
3. **Research grants** often require English proposals
4. **Collaboration** with international researchers needs English
5. **Career advancement** in STEM fields requires English proficiency

## Key differences from General English

| Feature | General English | Scientific English |
|---------|----------------|-------------------|
| Voice | Active ("We measured...") | Passive ("was measured...") |
| Person | "I", "you", "we" | "the researcher", "it", "one" |
| Contractions | "don't", "can't" | "do not", "cannot" |
| Vocabulary | Everyday words | Latin/Greek roots |
| Sentences | Variable length | Short and precise |
| Tense | Mixed | Present (facts), Past (methods), Present perfect (research) |

## Course overview

This course will cover:

1. **Module 1** · Scientific vocabulary and terminology
2. **Module 2** · Reading scientific papers
3. **Module 3** · Writing scientific abstracts and papers
4. **Module 4** · Oral presentations and conferences
5. **Module 5** · Grammar for scientific writing

Let's begin! 🎓"""},
                    {'type': 'mcq', 'title': 'Scientific English characteristics', 'question': 'Which of the following is a characteristic of Scientific English?',
                     'explanation': 'Scientific English favors passive voice for objectivity.',
                     'choices': [
                         {'text': 'Use of contractions like "don\'t"', 'correct': False, 'feedback': 'Contractions are avoided in scientific writing.'},
                         {'text': 'Use of passive voice for objectivity', 'correct': True, 'feedback': 'Correct! Passive voice emphasizes the process, not the researcher.'},
                         {'text': 'Colloquial expressions', 'correct': False, 'feedback': 'Scientific English is formal.'},
                         {'text': 'Personal opinions', 'correct': False, 'feedback': 'Scientific English is objective.'},
                     ]},
                    {'type': 'true_false', 'title': 'True or False? Scientific English', 'statements': [
                        {'statement': 'More than 90% of scientific journals publish in English.', 'is_true': True},
                        {'statement': 'Scientific English encourages the use of contractions.', 'is_true': False},
                        {'statement': 'Passive voice is commonly used in scientific writing.', 'is_true': True},
                        {'statement': 'Scientific English uses everyday vocabulary.', 'is_true': False},
                    ]},
                ],
            },
            {
                'order': 1, 'title': 'Greek and Latin Roots in Science', 'slug': 'greek-latin-roots',
                'minutes': 30, 'free_preview': True,
                'blocks': [
                    {'type': 'text', 'content': """# Greek and Latin Roots in Scientific English

## Why Greek and Latin?

Much of scientific terminology comes from **Greek** and **Latin** roots. Understanding these roots helps you:

- Decode unknown words
- Build vocabulary systematically
- Understand etymology (word origins)
- Communicate precisely

## Common Greek roots

| Root | Meaning | Example |
|------|---------|---------|
| **bio-** | life | biology, biography |
| **geo-** | earth | geology, geography |
| **chrono-** | time | chronology, chronic |
| **photo-** | light | photosynthesis, photograph |
| **thermo-** | heat | thermometer, thermodynamics |
| **hydro-** | water | hydrology, hydrogen |
| **micro-** | small | microscope, microorganism |
| **macro-** | large | macroeconomics, macromolecule |
| **tele-** | distant | telescope, telephone |
| **logy** | study of | biology, geology |

## Common Latin roots

| Root | Meaning | Example |
|------|---------|---------|
| **spec-** | to see | species, specimen, inspect |
| **dict-** | to say | dictate, predict |
| **duc-** | to lead | conduct, produce, reduce |
| **ject-** | to throw | inject, project, reject |
| **port-** | to carry | transport, export, import |
| **scrib-** | to write | describe, prescribe, subscribe |
| **tract-** | to pull | attract, extract, subtract |
| **vert-** | to turn | convert, invert, reverse |

## Prefixes

| Prefix | Meaning | Example |
|--------|---------|---------|
| **a-/an-** | without | abiotic, anaerobic |
| **anti-** | against | antibody, antioxidant |
| **auto-** | self | autotroph, automatic |
| **bi-** | two | binary, bilateral |
| **multi-** | many | multicellular, multifactorial |
| **peri-** | around | perimeter, peritoneum |
| **pre-** | before | predict, preliminary |
| **re-** | again | reproduce, regenerate |
| **sub-** | under | substrate, subatomic |
| **trans-** | across | transfer, transform |

## Suffixes

| Suffix | Meaning | Example |
|--------|---------|---------|
| **-ology** | study of | biology, ecology |
| **-itis** | inflammation | arthritis, hepatitis |
| **-osis** | condition | diagnosis, symbiosis |
| **-lysis** | breakdown | analysis, hydrolysis |
| **-genesis** | creation | pathogenesis, biogenesis |
| **-meter** | measure | thermometer, barometer |
| **-scope** | observe | microscope, telescope |
| **-graph** | record | photograph, electrocardiograph |"""},
                    {'type': 'mcq', 'title': 'Greek roots', 'question': 'The root "thermo-" means:',
                     'explanation': 'Thermo- comes from Greek "therme" meaning heat.',
                     'choices': [
                         {'text': 'Cold', 'correct': False},
                         {'text': 'Heat', 'correct': True, 'feedback': 'Correct! Thermometer measures heat.'},
                         {'text': 'Light', 'correct': False},
                         {'text': 'Time', 'correct': False},
                     ]},
                    {'type': 'mcq', 'title': 'Latin roots', 'question': 'The Latin root "port-" means:',
                     'explanation': 'Port- comes from Latin "portare" meaning to carry.',
                     'choices': [
                         {'text': 'To carry', 'correct': True, 'feedback': 'Correct! Transport = carry across.'},
                         {'text': 'To see', 'correct': False},
                         {'text': 'To write', 'correct': False},
                         {'text': 'To throw', 'correct': False},
                     ]},
                    {'type': 'fill_blank', 'title': 'Complete the word', 'instructions': 'Complete using the correct root.',
                     'text_with_blanks': "The study of life is called {{blank_1}}.\nThe instrument for measuring heat is a {{blank_2}}.\nThe process of breaking down is called {{blank_3}}.",
                     'answers': {'blank_1': ['biology', 'Biology'], 'blank_2': ['thermometer', 'Thermometer'], 'blank_3': ['analysis', 'Analysis']},
                     'explanation': 'Bio = life, -logy = study of. Thermo = heat, -meter = measure. -lysis = breakdown.'},
                    {'type': 'true_false', 'title': 'True or False? Roots', 'statements': [
                        {'statement': 'The prefix "anti-" means "against".', 'is_true': True},
                        {'statement': 'The suffix "-ology" means "small".', 'is_true': False},
                        {'statement': 'The root "hydro-" relates to water.', 'is_true': True},
                        {'statement': 'The prefix "bi-" means "three".', 'is_true': False},
                    ]},
                ],
            },
            {
                'order': 2, 'title': 'Numbers, Units, and Symbols', 'slug': 'numbers-units-symbols',
                'minutes': 25, 'free_preview': True,
                'blocks': [
                    {'type': 'text', 'content': """# Numbers, Units, and Symbols in Scientific English

## Writing numbers

In scientific English, numbers follow specific conventions:

- **Use numerals** for all measurements: "25 mL", "3.14", "100°C"
- **Spell out** numbers below 10 when not measurements: "three samples", "five trials"
- **Use scientific notation** for very large/small numbers: "1.5 × 10⁶" not "1,500,000"
- **Decimal point** (not comma): "3.14" (English) not "3,14" (French)
- **Thousands separator**: comma or space: "1,000" or "1 000"

## SI Units (Système International)

| Quantity | Unit | Symbol | Example |
|----------|------|--------|---------|
| Length | meter | m | 1.5 m |
| Mass | kilogram | kg | 2.3 kg |
| Time | second | s | 30 s |
| Temperature | kelvin | K | 298 K |
| Amount | mole | mol | 0.5 mol |
| Electric current | ampere | A | 2.5 A |

## Common prefixes

| Prefix | Symbol | Factor | Example |
|--------|--------|--------|---------|
| kilo- | k | 10³ | kilogram (kg) |
| centi- | c | 10⁻² | centimeter (cm) |
| milli- | m | 10⁻³ | milliliter (mL) |
| micro- | μ | 10⁻⁶ | microgram (μg) |
| nano- | n | 10⁻⁹ | nanometer (nm) |

## Mathematical expressions

| Expression | How to say it |
|------------|---------------|
| x = y | x equals y |
| x ≈ y | x is approximately equal to y |
| x ≠ y | x is not equal to y |
| x > y | x is greater than y |
| x < y | x is less than y |
| x² | x squared |
| x³ | x cubed |
| √x | the square root of x |
| ∑ | the sum of |
| ∫ | the integral of |
| Δx | delta x / the change in x |
| ∞ | infinity |

## Reading numbers aloud

- 0.5 → "zero point five" or "point five"
- 1/3 → "one third"
- 2/5 → "two fifths"
- 10⁶ → "ten to the sixth" or "ten to the power of six"
- 3.14 → "three point one four" (NOT "three point fourteen")"""},
                    {'type': 'mcq', 'title': 'Scientific notation', 'question': 'How would you write 1,500,000 in scientific notation?',
                     'explanation': 'Move the decimal 6 places to the left: 1.5 × 10⁶',
                     'choices': [
                         {'text': '1.5 × 10⁵', 'correct': False, 'feedback': 'That would be 150,000.'},
                         {'text': '1.5 × 10⁶', 'correct': True, 'feedback': 'Correct!'},
                         {'text': '15 × 10⁵', 'correct': False, 'feedback': 'Not standard form.'},
                         {'text': '0.15 × 10⁷', 'correct': False, 'feedback': 'Not standard form.'},
                     ]},
                    {'type': 'mcq', 'title': 'Reading numbers', 'question': 'How do you say "3.14" in English?',
                     'explanation': 'Each digit after the decimal point is read individually.',
                     'choices': [
                         {'text': 'Three point fourteen', 'correct': False, 'feedback': 'Each digit is read separately.'},
                         {'text': 'Three point one four', 'correct': True, 'feedback': 'Correct!'},
                         {'text': 'Three comma fourteen', 'correct': False, 'feedback': 'English uses a point, not a comma.'},
                         {'text': 'Three and fourteen', 'correct': False},
                     ]},
                    {'type': 'true_false', 'title': 'True or False? Numbers', 'statements': [
                        {'statement': 'In English, the decimal separator is a point (.), not a comma (,).', 'is_true': True},
                        {'statement': 'The symbol "μ" represents 10⁻³.', 'is_true': False},
                        {'statement': '"x > y" is read as "x is greater than y".', 'is_true': True},
                        {'statement': 'In scientific writing, you should use numerals for all measurements.', 'is_true': True},
                    ]},
                ],
            },
        ],
    },
    {
        'order': 1,
        'title': 'Reading Scientific Papers',
        'description': 'Learn to read, understand, and analyze scientific articles effectively.',
        'lessons': [
            {
                'order': 0, 'title': 'Structure of a Scientific Paper (IMRaD)', 'slug': 'imrad-structure',
                'minutes': 30, 'free_preview': True,
                'blocks': [
                    {'type': 'text', 'content': """# Structure of a Scientific Paper: IMRaD

## What is IMRaD?

Most scientific papers follow the **IMRaD** structure:

- **I** · Introduction
- **M** · Methods (or Materials and Methods)
- **R** · Results
- **aD** · and Discussion

Some papers also include:
- **Abstract** · a summary at the beginning
- **Conclusion** · at the end
- **References** · bibliography

## 1. Abstract

The abstract is a **150-250 word** summary of the entire paper. It contains:

- **Background** · why the study was done
- **Methods** · how it was done (briefly)
- **Results** · what was found
- **Conclusion** · what it means

> 💡 **Tip** : Always read the abstract first to decide if the paper is relevant.

## 2. Introduction

The introduction answers the question: **"Why did you do this study?"**

It follows a **funnel structure**:
1. **Broad context** · general background
2. **Specific problem** · what is unknown
3. **Research question** · what this study addresses
4. **Hypothesis** · what you expected to find

Key phrases in introductions:
- "Recent studies have shown that..."
- "However, little is known about..."
- "The aim of this study was to..."
- "We hypothesized that..."

## 3. Methods (Materials and Methods)

The methods section answers: **"How did you do it?"**

It must be detailed enough for **reproducibility** · another researcher should be able to repeat the study.

Common subsections:
- **Study design** · experimental, observational, etc.
- **Participants/Samples** · who or what was studied
- **Procedure** · step-by-step protocol
- **Measurements** · instruments and techniques
- **Statistical analysis** · tests used

Key phrases:
- "Data were collected using..."
- "Samples were analyzed by..."
- "Statistical analysis was performed using..."
- "The significance level was set at p < 0.05."

## 4. Results

The results section answers: **"What did you find?"**

It presents the data **without interpretation** · just the facts.

- Tables and figures are numbered: "Table 1", "Figure 2"
- Past tense is used: "The mean was 25.3..."
- No explanation · just results

Key phrases:
- "The results showed that..."
- "As shown in Figure 1..."
- "There was a significant difference between..."
- "No significant correlation was found."

## 5. Discussion

The discussion answers: **"What does it mean?"**

This is where you **interpret** the results:
1. Summarize the main findings
2. Compare with previous studies
3. Explain unexpected results
4. Discuss limitations
5. Suggest future research

Key phrases:
- "Our findings suggest that..."
- "This is consistent with previous studies..."
- "However, our results differ from..."
- "A limitation of this study is..."
- "Future research should..."

## Reading strategy

1. **Read the title and abstract** · is it relevant?
2. **Scan the figures and tables** · what data is presented?
3. **Read the introduction** · what is the research question?
4. **Skip to the discussion** · what are the main conclusions?
5. **Read the methods** · only if you need to evaluate quality
6. **Read the results** · in detail if you need the data"""},
                    {'type': 'mcq', 'title': 'IMRaD structure', 'question': 'What does the "M" in IMRaD stand for?',
                     'explanation': 'IMRaD = Introduction, Methods, Results, and Discussion.',
                     'choices': [
                         {'text': 'Measurements', 'correct': False},
                         {'text': 'Methods', 'correct': True, 'feedback': 'Correct! M = Methods (or Materials and Methods).'},
                         {'text': 'Models', 'correct': False},
                         {'text': 'Mathematics', 'correct': False},
                     ]},
                    {'type': 'mcq', 'title': 'Reading strategy', 'question': 'What should you read FIRST when evaluating a scientific paper?',
                     'explanation': 'The abstract helps you quickly determine if the paper is relevant.',
                     'choices': [
                         {'text': 'The methods section', 'correct': False},
                         {'text': 'The abstract', 'correct': True, 'feedback': 'Correct! Always start with the abstract.'},
                         {'text': 'The references', 'correct': False},
                         {'text': 'The conclusion', 'correct': False},
                     ]},
                    {'type': 'fill_blank', 'title': 'Complete the IMRaD section', 'instructions': 'Fill in the correct IMRaD section name.',
                     'text_with_blanks': "The {{blank_1}} section explains why the study was done.\nThe {{blank_2}} section presents the data without interpretation.\nThe {{blank_3}} section interprets the results.",
                     'answers': {'blank_1': ['Introduction', 'introduction'], 'blank_2': ['Results', 'results'], 'blank_3': ['Discussion', 'discussion']},
                     'explanation': 'Introduction = why, Results = what was found, Discussion = what it means.'},
                    {'type': 'true_false', 'title': 'True or False? Scientific papers', 'statements': [
                        {'statement': 'The abstract is typically 150-250 words.', 'is_true': True},
                        {'statement': 'The Results section includes interpretation of the data.', 'is_true': False},
                        {'statement': 'The Methods section must be detailed enough for reproducibility.', 'is_true': True},
                        {'statement': 'The Discussion section should not mention limitations.', 'is_true': False},
                    ]},
                ],
            },
            {
                'order': 1, 'title': 'Common Phrases in Scientific Papers', 'slug': 'scientific-phrases',
                'minutes': 25, 'free_preview': True,
                'blocks': [
                    {'type': 'text', 'content': """# Common Phrases in Scientific Papers

## Introduction phrases

### Stating what is known
- "It is well established that..."
- "Previous studies have demonstrated..."
- "Research has shown that..."
- "A growing body of evidence suggests..."
- "Several studies have reported..."

### Identifying the gap
- "However, little is known about..."
- "Despite these advances, the mechanism remains unclear."
- "To date, no study has examined..."
- "There is a paucity of data on..."
- "This area remains understudied."

### Stating the objective
- "The aim of this study was to..."
- "We sought to investigate..."
- "This study aimed to determine..."
- "The objective was to evaluate..."
- "We hypothesized that..."

## Methods phrases

### Describing procedures
- "Data were collected using..."
- "Samples were analyzed by means of..."
- "The experiment was conducted in accordance with..."
- "Participants were randomly assigned to..."
- "Measurements were taken at intervals of..."

### Statistical analysis
- "Statistical analysis was performed using..."
- "Differences were assessed by..."
- "The significance level was set at p < 0.05."
- "Correlations were evaluated using Pearson's coefficient."
- "Data are expressed as mean ± standard deviation."

## Results phrases

### Reporting findings
- "The results showed that..."
- "We found that..."
- "As shown in Figure 1, ..."
- "There was a significant difference between..."
- "No significant correlation was found between..."
- "The mean value was 25.3 ± 2.1."

### Comparing groups
- "Compared to the control group, ..."
- "The treatment group exhibited..."
- "Both groups showed similar..."
- "The difference was statistically significant (p < 0.01)."

## Discussion phrases

### Interpreting results
- "Our findings suggest that..."
- "These results indicate..."
- "This finding is consistent with..."
- "The data support the hypothesis that..."
- "One possible explanation is that..."

### Comparing with other studies
- "This is in agreement with the findings of..."
- "Our results are consistent with previous reports..."
- "In contrast to [Author et al.], we found..."
- "These results contradict earlier studies that..."

### Limitations
- "A limitation of this study is..."
- "Several limitations should be noted."
- "The sample size was relatively small."
- "These findings may not be generalizable to..."
- "Further studies are needed to confirm..."

### Future work
- "Future research should focus on..."
- "It would be interesting to investigate..."
- "Further studies are warranted to..."
- "Additional research is needed to..."
"""},
                    {'type': 'mcq', 'title': 'Introduction phrases', 'question': 'Which phrase is used to identify a research gap?',
                     'explanation': 'Identifying a gap means saying what is NOT known yet.',
                     'choices': [
                         {'text': 'It is well established that...', 'correct': False, 'feedback': 'This states what IS known.'},
                         {'text': 'However, little is known about...', 'correct': True, 'feedback': 'Correct! This identifies what is NOT known.'},
                         {'text': 'The results showed that...', 'correct': False, 'feedback': 'This is a results phrase.'},
                         {'text': 'Data were collected using...', 'correct': False, 'feedback': 'This is a methods phrase.'},
                     ]},
                    {'type': 'mcq', 'title': 'Results vs Discussion', 'question': 'Which phrase belongs in the Results section (not Discussion)?',
                     'explanation': 'Results present facts; Discussion interprets them.',
                     'choices': [
                         {'text': 'Our findings suggest that...', 'correct': False, 'feedback': 'This is interpretation · belongs in Discussion.'},
                         {'text': 'The mean value was 25.3 ± 2.1.', 'correct': True, 'feedback': 'Correct! This is a factual report.'},
                         {'text': 'This is consistent with previous studies.', 'correct': False, 'feedback': 'This is comparison · belongs in Discussion.'},
                         {'text': 'One possible explanation is that...', 'correct': False, 'feedback': 'This is interpretation.'},
                     ]},
                    {'type': 'true_false', 'title': 'True or False? Scientific phrases', 'statements': [
                        {'statement': '"To date, no study has examined..." is used to identify a research gap.', 'is_true': True},
                        {'statement': '"As shown in Figure 1" is a phrase used in the Discussion section.', 'is_true': False},
                        {'statement': '"A limitation of this study is..." is typically found in the Discussion.', 'is_true': True},
                        {'statement': 'Contractions like "don\'t" are commonly used in scientific papers.', 'is_true': False},
                    ]},
                ],
            },
        ],
    },
    {
        'order': 2,
        'title': 'Writing Scientific Abstracts & Papers',
        'description': 'Learn to write clear, concise scientific abstracts and papers.',
        'lessons': [
            {
                'order': 0, 'title': 'Writing a Scientific Abstract', 'slug': 'writing-abstract',
                'minutes': 30, 'free_preview': True,
                'blocks': [
                    {'type': 'text', 'content': """# Writing a Scientific Abstract

## What is an abstract?

An abstract is a **self-contained** summary of your research. It should allow a reader to understand:
- What you did
- How you did it
- What you found
- Why it matters

## The 4-part structure

A good abstract has **four parts** (roughly 2-3 sentences each):

### 1. Background & Objective (Why?)
State the problem and why it matters.
- "X is a major problem in..."
- "Previous studies have shown..."
- "However, it remains unclear whether..."
- "The aim of this study was to..."

### 2. Methods (How?)
Briefly describe what you did.
- "We conducted a study involving..."
- "Data were collected from..."
- "Samples were analyzed using..."
- "Statistical analysis was performed with..."

### 3. Results (What?)
State your main findings · be specific with numbers.
- "The results showed that..."
- "We found a significant difference..."
- "The mean was 25.3 (SD = 2.1)..."
- "There was a positive correlation between..."

### 4. Conclusion (So what?)
State the significance.
- "These findings suggest that..."
- "This study demonstrates..."
- "The results have implications for..."
- "This approach could be applied to..."

## Tips for writing

- **Word count**: usually 150-250 words (check journal guidelines)
- **Tense**: Past tense for methods and results; present tense for background and conclusion
- **Voice**: Passive is common but active is increasingly accepted
- **No references**: Do not cite other papers in the abstract
- **No abbreviations**: Unless defined first
- **Specific numbers**: Include key quantitative results

## Example abstract

> **Background**: Malaria remains a leading cause of mortality in sub-Saharan Africa. However, the effectiveness of vector control strategies in urban settings is poorly understood. This study aimed to evaluate the impact of insecticide-treated bed nets (ITNs) on malaria incidence in urban Lomé, Togo.
>
> **Methods**: A prospective cohort study was conducted over 12 months involving 500 households. Participants were surveyed monthly, and malaria cases were confirmed by rapid diagnostic tests. Data were analyzed using Poisson regression.
>
> **Results**: ITN usage was associated with a 47% reduction in malaria incidence (IRR = 0.53, 95% CI: 0.41-0.69, p < 0.001). The protective effect was strongest among children under 5 years (IRR = 0.31).
>
> **Conclusion**: These findings demonstrate that ITNs remain highly effective in urban settings. The results support continued investment in ITN distribution programs in urban African areas."""},
                    {'type': 'mcq', 'title': 'Abstract structure', 'question': 'How many parts does a standard scientific abstract have?',
                     'explanation': 'Background, Methods, Results, Conclusion.',
                     'choices': [
                         {'text': '2', 'correct': False},
                         {'text': '3', 'correct': False},
                         {'text': '4', 'correct': True, 'feedback': 'Correct! Background, Methods, Results, Conclusion.'},
                         {'text': '6', 'correct': False},
                     ]},
                    {'type': 'mcq', 'title': 'Abstract rules', 'question': 'Which of the following should you NOT include in an abstract?',
                     'explanation': 'Abstracts should be self-contained without references.',
                     'choices': [
                         {'text': 'Key quantitative results', 'correct': False, 'feedback': 'You should include numbers.'},
                         {'text': 'References to other papers', 'correct': True, 'feedback': 'Correct! No citations in the abstract.'},
                         {'text': 'The main conclusion', 'correct': False, 'feedback': 'You should include the conclusion.'},
                         {'text': 'The study objective', 'correct': False, 'feedback': 'You should include the objective.'},
                     ]},
                    {'type': 'fill_blank', 'title': 'Complete the abstract phrases',
                     'text_with_blanks': "The {{blank_1}} of this study was to evaluate the impact of the treatment.\nThe results {{blank_2}} that the treatment was effective.\nThese findings {{blank_3}} that the treatment can be recommended.",
                     'answers': {'blank_1': ['aim', 'objective', 'goal'], 'blank_2': ['showed', 'demonstrated', 'indicated'], 'blank_3': ['suggest', 'demonstrate', 'indicate']},
                     'explanation': 'aim/objective for the goal; showed/demonstrated for results; suggest/demonstrate for conclusion.'},
                    {'type': 'true_false', 'title': 'True or False? Abstracts', 'statements': [
                        {'statement': 'An abstract should typically be 150-250 words.', 'is_true': True},
                        {'statement': 'You should use present tense for methods in the abstract.', 'is_true': False},
                        {'statement': 'Abbreviations should be defined when first used in the abstract.', 'is_true': True},
                        {'statement': 'An abstract should include detailed statistical methods.', 'is_true': False},
                    ]},
                ],
            },
            {
                'order': 1, 'title': 'Writing Clear Scientific Sentences', 'slug': 'clear-sentences',
                'minutes': 25, 'free_preview': True,
                'blocks': [
                    {'type': 'text', 'content': """# Writing Clear Scientific Sentences

## Principles of scientific writing

### 1. Be concise
Remove unnecessary words.

❌ "Due to the fact that the temperature was high..." (9 words)
✅ "Because the temperature was high..." (6 words)

❌ "It has been demonstrated by previous studies that..." (9 words)
✅ "Previous studies show that..." (5 words)

### 2. Be precise
Use exact terms.

❌ "The stuff was put in the thing."
✅ "The sample was placed in the centrifuge."

❌ "A lot of bacteria were found."
✅ "Approximately 10⁶ CFU/mL of bacteria were detected."

### 3. Be objective
Avoid personal language.

❌ "I think the results are amazing."
✅ "The results indicate a significant improvement."

❌ "We were surprised to find..."
✅ "Unexpectedly, the data showed..."

### 4. Use active or passive appropriately

**Passive** (focus on the action):
- "The samples were analyzed by HPLC."
- "Data were collected over 12 months."

**Active** (focus on the doer · increasingly preferred):
- "We analyzed the samples by HPLC."
- "We collected data over 12 months."

### 5. One idea per sentence

❌ "The samples were collected from three sites and then analyzed using mass spectrometry which revealed the presence of five compounds that had not been previously reported in this region."

✅ "Samples were collected from three sites. Mass spectrometry analysis revealed five compounds not previously reported in this region."

## Common mistakes to avoid

### Wordiness
| Wordy | Concise |
|-------|---------|
| in order to | to |
| due to the fact that | because |
| in the event that | if |
| a majority of | most |
| a number of | several |
| at the present time | currently |
| in the near future | soon |
| it has been shown that | (delete · just state the fact) |

### Misplaced modifiers
❌ "We only tested the samples at 25°C." (implies you did nothing else)
✅ "We tested the samples only at 25°C." (correct · only 25°C was used)

### Subject-verb agreement
❌ "The data shows..." (data is plural)
✅ "The data show..."

❌ "Each of the samples were analyzed."
✅ "Each of the samples was analyzed."

## Linking words for flow

| Purpose | Words |
|---------|-------|
| Addition | moreover, furthermore, in addition |
| Contrast | however, nevertheless, in contrast |
| Cause | therefore, consequently, as a result |
| Sequence | first, then, subsequently, finally |
| Example | for instance, specifically, such as |
| Summary | in summary, overall, to conclude |"""},
                    {'type': 'mcq', 'title': 'Conciseness', 'question': 'Which sentence is more concise?',
                     'explanation': 'Remove unnecessary words while keeping the meaning.',
                     'choices': [
                         {'text': 'Due to the fact that the temperature was high', 'correct': False, 'feedback': 'Wordy.'},
                         {'text': 'Because the temperature was high', 'correct': True, 'feedback': 'Correct! Same meaning, fewer words.'},
                         {'text': 'Owing to the circumstance that the temperature was elevated', 'correct': False, 'feedback': 'Very wordy.'},
                         {'text': 'On account of the fact that the temperature was high', 'correct': False, 'feedback': 'Wordy.'},
                     ]},
                    {'type': 'mcq', 'title': 'Subject-verb agreement', 'question': 'Which sentence is grammatically correct?',
                     'explanation': '"Data" is the plural of "datum".',
                     'choices': [
                         {'text': 'The data shows a clear trend.', 'correct': False, 'feedback': '"Data" is plural, so it should be "show".'},
                         {'text': 'The data show a clear trend.', 'correct': True, 'feedback': 'Correct! "Data" is plural.'},
                         {'text': 'The data showing a clear trend.', 'correct': False, 'feedback': 'Not a complete sentence.'},
                         {'text': 'The data shown a clear trend.', 'correct': False, 'feedback': 'Grammatically incorrect.'},
                     ]},
                    {'type': 'true_false', 'title': 'True or False? Writing', 'statements': [
                        {'statement': 'In scientific writing, each sentence should contain one main idea.', 'is_true': True},
                        {'statement': 'The word "data" is singular.', 'is_true': False},
                        {'statement': 'Active voice is increasingly preferred in scientific writing.', 'is_true': True},
                        {'statement': 'Contractions like "can\'t" should be used in scientific papers.', 'is_true': False},
                    ]},
                ],
            },
        ],
    },
    {
        'order': 3,
        'title': 'Oral Presentations & Conferences',
        'description': 'Present your research confidently in English at conferences and seminars.',
        'lessons': [
            {
                'order': 0, 'title': 'Structuring a Scientific Presentation', 'slug': 'presentation-structure',
                'minutes': 30, 'free_preview': True,
                'blocks': [
                    {'type': 'text', 'content': """# Structuring a Scientific Presentation

## The 10-minute rule

A typical conference presentation is **10-15 minutes**. Plan for:
- **1 slide per minute** (maximum)
- **3 main parts**: Introduction → Methods & Results → Discussion

## Presentation structure

### 1. Title Slide (30 sec)
- Title of your research
- Your name and affiliation
- Co-authors and institutions
- Conference name/date

### 2. Outline (15 sec)
- "Today, I will discuss..."
- "My presentation is divided into three parts..."

### 3. Introduction (2-3 min)
- **Hook** · start with a question or striking fact
- **Background** · what is known
- **Gap** · what is unknown
- **Objective** · what you did

> 💡 **Tip** : Use a question to engage the audience: "Did you know that...?"

### 4. Methods (2 min)
- Keep it brief · the audience trusts you did it correctly
- Use **diagrams** instead of text
- Only explain what is necessary to understand the results

### 5. Results (3-4 min)
- This is the **most important** part
- Show **one key result per slide**
- Use clear figures, not tables (tables are hard to read)
- Highlight the key finding with color or arrows

Phrases:
- "As you can see in this figure..."
- "The key finding here is..."
- "What's interesting to note is..."

### 6. Discussion (2 min)
- What do the results mean?
- How do they compare with other studies?
- What are the limitations?
- What are the implications?

### 7. Conclusion (1 min)
- Summarize in **one sentence**
- "In conclusion, our study demonstrates that..."
- Future directions

### 8. Acknowledgments + Q&A
- Thank collaborators and funders
- "Thank you for your attention. I'm happy to answer any questions."

## Slide design tips

- **One idea per slide**
- **Maximum 6 lines** of text per slide
- **Font size**: at least 24pt
- **Contrast**: dark text on light background (or vice versa)
- **Images**: high quality, relevant
- **Animation**: minimal, only if it helps understanding
- **Consistency**: same fonts, colors, layout throughout

## Handling questions

- **Listen carefully** · let them finish
- **Repeat** the question (for the audience)
- **Take a moment** to think
- **Admit** if you don't know: "That's an interesting question. I don't have the data to answer that, but..."
- **Be concise** · 30-60 seconds per answer

## Useful phrases

### Starting
- "Good morning/afternoon, everyone."
- "Thank you for the introduction."
- "I'm delighted to be here today."

### Transitioning
- "Moving on to the results..."
- "This brings me to my next point..."
- "Let's now look at..."

### Emphasizing
- "I'd like to draw your attention to..."
- "The key point here is..."
- "It's worth noting that..."

### Concluding
- "To summarize..."
- "In conclusion..."
- "Let me wrap up by saying..."

### Q&A
- "That's a great question."
- "Could you please clarify your question?"
- "If I understand your question correctly..."""},
                    {'type': 'mcq', 'title': 'Presentation timing', 'question': 'How many slides should you plan for a 10-minute presentation?',
                     'explanation': 'Plan for about 1 slide per minute.',
                     'choices': [
                         {'text': '5 slides', 'correct': False, 'feedback': 'Too few · you will rush.'},
                         {'text': '10 slides', 'correct': True, 'feedback': 'Correct! About 1 slide per minute.'},
                         {'text': '25 slides', 'correct': False, 'feedback': 'Too many · you will rush.'},
                         {'text': '50 slides', 'correct': False, 'feedback': 'Way too many!'},
                     ]},
                    {'type': 'mcq', 'title': 'Results presentation', 'question': 'What is the best way to present results in a talk?',
                     'explanation': 'Figures are easier to read than tables on a screen.',
                     'choices': [
                         {'text': 'Detailed tables with all data', 'correct': False, 'feedback': 'Tables are hard to read on slides.'},
                         {'text': 'Clear figures with one key result per slide', 'correct': True, 'feedback': 'Correct! One key result per slide.'},
                         {'text': 'Long paragraphs describing results', 'correct': False, 'feedback': 'Too much text.'},
                         {'text': 'No visuals, just talk', 'correct': False, 'feedback': 'Visuals are essential.'},
                     ]},
                    {'type': 'true_false', 'title': 'True or False? Presentations', 'statements': [
                        {'statement': 'You should use font size 12pt for slide text.', 'is_true': False},
                        {'statement': 'It is okay to say "I don\'t know" during Q&A.', 'is_true': True},
                        {'statement': 'Each slide should contain one main idea.', 'is_true': True},
                        {'statement': 'You should read your slides word for word.', 'is_true': False},
                    ]},
                ],
            },
            {
                'order': 1, 'title': 'Pronunciation for Scientific English', 'slug': 'pronunciation',
                'minutes': 25, 'free_preview': True,
                'blocks': [
                    {'type': 'text', 'content': """# Pronunciation for Scientific English

## Commonly mispronounced scientific words

| Word | ❌ Wrong | ✅ Correct |
|------|---------|-----------|
| analysis | a-NAL-i-sis | a-NAL-uh-sis |
| analyses (plural) | a-NAL-i-sees | uh-NAL-uh-seez |
| hypothesis | hi-PO-thee-sis | hy-POTH-uh-sis |
| hypotheses | hi-PO-thee-seez | hy-POTH-uh-seez |
| data | DAH-ta | DAY-tuh |
| phenomenon | phe-NOM-e-non | fuh-NOM-uh-non |
| phenomena | phe-NOM-e-na | fuh-NOM-uh-nuh |
| nucleus | NU-cle-us | NEW-klee-us |
| nuclei | NU-clee-i | NEW-klee-eye |
| matrix | MA-triks | MAY-triks |
| matrices | ma-TRI-sees | MAY-truh-seez |
| species | SPE-shies | SPEE-sheez |
| apparatus | a-pa-RA-tus | ap-uh-RAT-us |
| literature | li-te-ra-TURE | LIT-ur-uh-chur |

## Word stress patterns

### Stress on the FIRST syllable
- **PHOtograph**, **PHOtographer**, **PHOtographic**
- **SCIENCE**, **SCIentific**, **SCIentist**
- **REsearch** (noun), **reSEARCH** (verb)
- **REcord** (noun), **reCORD** (verb)

### Stress changes with suffix
| Noun (stress on 1st) | Adjective (stress shifts) |
|----------------------|--------------------------|
| PHOtograph | phoTOGraphic |
| TELEgraph | teLEGraphic |
| BIOlogy | biOLogical |
| ECology | eCOSystem |

### Numbers and symbols
- 0.05 → "zero point zero five" or "point zero five"
- 10⁻³ → "ten to the minus three"
- ± → "plus or minus"
- ≈ → "approximately"
- °C → "degrees Celsius" (NOT "degrees centigrade" in modern usage)
- μg → "micrograms"
- mL → "milliliters"

## Intonation in presentations

### Rising intonation
- Questions: "Is this significant? ↗"
- Lists (before the last item): "We measured weight, ↗ height, ↗ and BMI. ↘"

### Falling intonation
- Statements: "The results were significant. ↘"
- Commands: "Please look at this slide. ↘"
- Wh- questions: "What is the mechanism? ↘"

## Practice tips

1. **Record yourself** and listen back
2. **Use a mirror** to check your mouth movements
3. **Slow down** · non-native speakers often speak too fast
4. **Pause** between sections · 2-3 seconds of silence is powerful
5. **Emphasize key words** · "The results were **significant**."""},
                    {'type': 'mcq', 'title': 'Word stress', 'question': 'Where is the stress in the word "scientific"?',
                     'explanation': 'sci-en-TIF-ic · stress on the 3rd syllable.',
                     'choices': [
                         {'text': 'SCI-en-tif-ic (1st syllable)', 'correct': False},
                         {'text': 'sci-EN-tif-ic (2nd syllable)', 'correct': False},
                         {'text': 'sci-en-TIF-ic (3rd syllable)', 'correct': True, 'feedback': 'Correct!'},
                         {'text': 'sci-en-tif-IC (4th syllable)', 'correct': False},
                     ]},
                    {'type': 'mcq', 'title': 'Pronunciation', 'question': 'How is "data" most commonly pronounced in scientific English?',
                     'explanation': 'In modern scientific English, "DAY-tuh" is the most common pronunciation.',
                     'choices': [
                         {'text': 'DAH-tah', 'correct': False, 'feedback': 'British traditional, less common now.'},
                         {'text': 'DAY-tuh', 'correct': True, 'feedback': 'Correct! Most common in scientific contexts.'},
                         {'text': 'DAH-tuh', 'correct': False},
                         {'text': 'DATT-uh', 'correct': False},
                     ]},
                    {'type': 'true_false', 'title': 'True or False? Pronunciation', 'statements': [
                        {'statement': 'The plural of "hypothesis" is "hypotheses".', 'is_true': True},
                        {'statement': 'In "photograph" vs "photographic", the stress stays on the same syllable.', 'is_true': False},
                        {'statement': 'The symbol "°C" is read as "degrees Celsius".', 'is_true': True},
                        {'statement': 'Non-native speakers should speak fast to sound fluent.', 'is_true': False},
                    ]},
                ],
            },
        ],
    },
    {
        'order': 4,
        'title': 'Grammar for Scientific Writing',
        'description': 'Master the essential grammar patterns used in scientific English.',
        'lessons': [
            {
                'order': 0, 'title': 'Tenses in Scientific Writing', 'slug': 'tenses-scientific',
                'minutes': 30, 'free_preview': True,
                'blocks': [
                    {'type': 'text', 'content': """# Tenses in Scientific Writing

## Which tense to use?

The tense you choose depends on the **section** of the paper and what you are describing.

## Overview

| Section | Tense | Why |
|---------|-------|-----|
| Abstract · Background | Present | General truths |
| Abstract · Methods | Past | What you did |
| Abstract · Results | Past | What you found |
| Abstract · Conclusion | Present | What it means now |
| Introduction | Present | Established facts |
| Introduction · prior work | Present perfect | What has been done |
| Methods | Past | What you did |
| Results | Past | What you found |
| Discussion | Present | Interpreting results |
| Discussion · prior work | Present / Present perfect | Comparing |

## 1. Present Simple

Use for **established facts** and **general truths**:
- "Water boils at 100°C."
- "DNA contains four bases."
- "Malaria is caused by Plasmodium parasites."

Use in **Introduction** for background:
- "Cancer is a leading cause of death worldwide."
- "Photosynthesis converts light energy into chemical energy."

Use in **Discussion** for interpretation:
- "These results indicate that..."
- "The data suggest that..."

## 2. Past Simple

Use for **what you did** (Methods) and **what you found** (Results):
- "We collected samples from three sites."
- "The samples were analyzed by HPLC."
- "The mean temperature was 25.3°C."
- "No significant difference was found."

## 3. Present Perfect

Use for **previous research** (what has been done up to now):
- "Several studies have investigated this phenomenon."
- "Little research has been conducted on..."
- "This method has been widely used since 2010."

Use to connect past research to the present:
- "Previous studies have shown that..."
- "This approach has not been previously applied to..."

## 4. Future

Rarely used in scientific writing, but can appear in:
- **Future research**: "Future studies will need to..."
- **Protocols**: "The solution will be incubated for 24 hours."

## Common mistakes

### Mixing tenses
❌ "The data shows that the treatment was effective. This suggests that..."
✅ "The data show that the treatment was effective. This suggests that..."

### Using present for methods
❌ "We collect samples from three sites and analyze them by HPLC."
✅ "We collected samples from three sites and analyzed them by HPLC."

### Using past for established facts
❌ "Water boiled at 100°C at sea level."
✅ "Water boils at 100°C at sea level."

## Quick reference

| If you are describing... | Use... | Example |
|--------------------------|--------|---------|
| A general truth | Present | "Light travels at 3×10⁸ m/s." |
| What you did | Past | "We measured the absorbance." |
| What you found | Past | "The value was 0.45." |
| What others have done | Present perfect | "Smith et al. have reported..." |
| What the results mean | Present | "This indicates that..." |
| What should be done next | Future / Conditional | "Future studies should examine..." |"""},
                    {'type': 'mcq', 'title': 'Tense for Methods', 'question': 'Which tense should you use in the Methods section?',
                     'explanation': 'Methods describe what you DID, so use past tense.',
                     'choices': [
                         {'text': 'Present simple', 'correct': False, 'feedback': 'Present is for general truths.'},
                         {'text': 'Past simple', 'correct': True, 'feedback': 'Correct! Methods = what you did = past.'},
                         {'text': 'Future', 'correct': False},
                         {'text': 'Present perfect', 'correct': False, 'feedback': 'Present perfect is for prior research.'},
                     ]},
                    {'type': 'mcq', 'title': 'Tense for established facts', 'question': 'Which tense for: "Water ___ at 100°C."',
                     'explanation': 'This is a general truth · always true.',
                     'choices': [
                         {'text': 'boiled', 'correct': False, 'feedback': 'Past implies it no longer boils at 100°C.'},
                         {'text': 'boils', 'correct': True, 'feedback': 'Correct! General truth = present.'},
                         {'text': 'has boiled', 'correct': False},
                         {'text': 'will boil', 'correct': False},
                     ]},
                    {'type': 'fill_blank', 'title': 'Choose the correct tense',
                     'text_with_blanks': "Water {{blank_1}} at 100°C at sea level. (present)\nWe {{blank_2}} samples from three sites. (past)\nPrevious studies {{blank_3}} shown that the method is effective. (present perfect)",
                     'answers': {'blank_1': ['boils'], 'blank_2': ['collected', 'obtained'], 'blank_3': ['have']},
                     'explanation': 'Present for facts, past for what you did, present perfect for prior research.'},
                    {'type': 'true_false', 'title': 'True or False? Tenses', 'statements': [
                        {'statement': 'Use past tense in the Results section.', 'is_true': True},
                        {'statement': 'Use present perfect to describe what you did in your experiment.', 'is_true': False},
                        {'statement': 'Use present tense in the Discussion to interpret results.', 'is_true': True},
                        {'statement': 'General truths like "DNA contains four bases" use past tense.', 'is_true': False},
                    ]},
                ],
            },
            {
                'order': 1, 'title': 'Passive Voice & Hedging', 'slug': 'passive-hedging',
                'minutes': 25, 'free_preview': True,
                'blocks': [
                    {'type': 'text', 'content': """# Passive Voice & Hedging in Scientific Writing

## Passive Voice

### Why use passive voice?

In scientific writing, **what was done** is more important than **who did it**:
- "The samples were analyzed." (focus on the samples)
- "We analyzed the samples." (focus on the researchers)

### Forming the passive

| Tense | Active | Passive |
|-------|--------|---------|
| Present | "We analyze" | "is/are analyzed" |
| Past | "We analyzed" | "was/were analyzed" |
| Present perfect | "We have analyzed" | "has/have been analyzed" |
| Future | "We will analyze" | "will be analyzed" |
| Modal | "We must analyze" | "must be analyzed" |

### When to use passive vs active

**Use passive when:**
- The doer is unknown: "The samples were contaminated."
- The doer is irrelevant: "The solution was heated to 80°C."
- Emphasizing the process: "DNA was extracted using..."

**Use active when:**
- You are describing your own actions: "We collected data from..."
- The doer matters: "Smith et al. reported..."
- For clarity (active is often clearer)

> 💡 **Modern trend**: Many journals now encourage active voice: "We collected samples" instead of "Samples were collected."

## Hedging

### What is hedging?

**Hedging** is the use of cautious language to express uncertainty. In science, we rarely "prove" things · we **suggest**, **indicate**, or **support**.

### Hedging verbs

| Strong (avoid) | Moderate (good) | Weak (too cautious) |
|----------------|-----------------|---------------------|
| prove | suggest | might suggest |
| demonstrate | indicate | could indicate |
| show | support | may support |
| establish | imply | |
| confirm | propose | |

### Hedging with adverbs

- "The results **suggest** that..."
- "This **may indicate** that..."
- "It **is likely that**..."
- "These findings **support the hypothesis** that..."
- "This **could be explained by**..."

### Examples

❌ **Too strong**: "Our results prove that climate change causes extinction."
✅ **Hedged**: "Our results suggest that climate change may contribute to extinction."

❌ **Too strong**: "This demonstrates that the treatment cures cancer."
✅ **Hedged**: "This indicates that the treatment may be effective against certain types of cancer."

### When NOT to hedge

- **Methods**: "The samples were centrifuged at 10,000 rpm for 10 minutes." (no hedging needed · this is a fact)
- **Established facts**: "DNA contains four nucleotide bases." (no hedging · this is proven)

## Modal verbs for hedging

| Modal | Strength | Example |
|-------|----------|---------|
| will/can | Strong | "This will improve..." |
| should | Moderate | "This should reduce..." |
| may/might | Weak | "This may reduce..." |
| could | Possibility | "This could explain..." |
| would | Conditional | "This would suggest..." |

## Common hedging phrases

- "It is possible that..."
- "These findings suggest that..."
- "One interpretation is that..."
- "The evidence points to..."
- "It appears that..."
- "There is evidence to suggest..."
- "This is consistent with..."
- "These results support the notion that..." """},
                    {'type': 'mcq', 'title': 'Passive voice', 'question': 'Which is the correct passive form of "We analyzed the samples"?',
                     'explanation': 'Past passive = was/were + past participle.',
                     'choices': [
                         {'text': 'The samples is analyzed.', 'correct': False, 'feedback': 'Wrong tense and number.'},
                         {'text': 'The samples were analyzed.', 'correct': True, 'feedback': 'Correct! Past passive.'},
                         {'text': 'The samples are analyzed.', 'correct': False, 'feedback': 'This is present passive.'},
                         {'text': 'The samples will be analyzed.', 'correct': False, 'feedback': 'This is future passive.'},
                     ]},
                    {'type': 'mcq', 'title': 'Hedging', 'question': 'Which sentence is appropriately hedged for a scientific paper?',
                     'explanation': 'Scientific claims should be cautious, not absolute.',
                     'choices': [
                         {'text': 'Our results prove that the drug cures all cancers.', 'correct': False, 'feedback': 'Too strong · "prove" and "all" are absolute.'},
                         {'text': 'Our results suggest that the drug may be effective against certain cancers.', 'correct': True, 'feedback': 'Correct! Appropriately hedged.'},
                         {'text': 'Our results might possibly perhaps indicate something about cancer.', 'correct': False, 'feedback': 'Over-hedged · too many qualifiers.'},
                         {'text': 'Cancer is cured by this drug.', 'correct': False, 'feedback': 'Too strong and absolute.'},
                     ]},
                    {'type': 'fill_blank', 'title': 'Complete with hedging words',
                     'text_with_blanks': "Our results {{blank_1}} that the treatment may be effective.\nThe evidence {{blank_2}} to a possible link between the variables.\nIt is {{blank_3}} that the mechanism involves oxidative stress.",
                     'answers': {'blank_1': ['suggest', 'indicate'], 'blank_2': ['points'], 'blank_3': ['possible', 'likely']},
                     'explanation': 'suggest/indicate for results, points for evidence, possible/likely for speculation.'},
                    {'type': 'true_false', 'title': 'True or False? Passive & Hedging', 'statements': [
                        {'statement': 'In scientific writing, "prove" should be used carefully and rarely.', 'is_true': True},
                        {'statement': 'Passive voice is always better than active voice in science.', 'is_true': False},
                        {'statement': '"The samples were contaminated" is an example of passive voice.', 'is_true': True},
                        {'statement': 'Hedging should be used in the Methods section for procedures.', 'is_true': False},
                    ]},
                ],
            },
        ],
    },
]
