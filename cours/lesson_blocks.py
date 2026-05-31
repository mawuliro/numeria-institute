"""Shared LessonBlock serializer for student views and admin previews."""
import base64
import json
import random

from .models import (
    LessonBlock, CodeExercise, StudentCodeSubmission,
    MCQExercise, MCQGrade, MCQChoice,
    FillBlankExercise, FillBlankGrade,
    TrueFalseExercise, TrueFalseGrade,
    CodeOrderExercise, CodeOrderGrade,
    MatchingExercise, MatchingGrade,
    ShortAnswerExercise, ShortAnswerGrade,
    convertir_url_youtube,
)


def build_lesson_blocks(*, course_lesson=None, formation_lesson=None, user=None, preview=False):
    """
    Build sanitized block dicts for lesson_blocks_render.html.
    Exactly one of course_lesson or formation_lesson must be provided.
    """
    if bool(course_lesson) == bool(formation_lesson):
        return []

    filter_kw = (
        {'course_lesson': course_lesson}
        if course_lesson else
        {'formation_lesson': formation_lesson}
    )
    blocks_qs = LessonBlock.objects.filter(**filter_kw).order_by('order')
    if not blocks_qs.exists():
        return []

    solved_ids = set()
    if user and not preview:
        lb_filter = (
            {'exercise__lesson_blocks__course_lesson': course_lesson}
            if course_lesson else
            {'exercise__lesson_blocks__formation_lesson': formation_lesson}
        )
        solved_ids = set(
            StudentCodeSubmission.objects.filter(
                student=user, is_correct=True, **lb_filter,
            ).values_list('exercise_id', flat=True)
        )

    user_id = user.id if user else 0
    result = []

    for block in blocks_qs:
        bd = {'id': block.id, 'type': block.block_type, 'order': block.order}

        if block.block_type == 'text':
            bd['text_content'] = block.text_content

        elif block.block_type == 'video':
            bd['video_url'] = block.video_url
            bd['video_caption'] = block.video_caption
            if block.video_url:
                bd['embed_url'] = convertir_url_youtube(block.video_url)

        elif block.block_type == 'sandbox':
            bd['title'] = block.sandbox_title or 'Essaie toi-même'
            bd['initial_code'] = block.sandbox_initial_code

        elif block.block_type == 'exercise' and block.code_exercise:
            ex = block.code_exercise
            tc_b64 = base64.b64encode(ex.test_code.encode()).decode() if ex.test_code else ''
            bd.update({
                'exercise_id': ex.id,
                'title': ex.title,
                'instructions': ex.instructions,
                'starter_code': ex.starter_code,
                'expected_output': ex.expected_output,
                'evaluation_mode': ex.evaluation_mode,
                'difficulty': ex.difficulty,
                'hint': ex.hint,
                'max_attempts': ex.max_attempts,
                'points': ex.points,
                'test_code_b64': tc_b64,
                'is_solved': ex.id in solved_ids,
                'attempts_used': 0,
            })

        elif block.block_type == 'mcq' and block.mcq_exercise:
            mcq = block.mcq_exercise
            grade = MCQGrade.objects.filter(student=user, exercise=mcq).first() if user and not preview else None
            choices = list(mcq.choices.order_by('order'))
            exhausted = grade and mcq.max_attempts > 0 and grade.attempts_count >= mcq.max_attempts
            reveal = preview or (grade and (grade.is_solved or exhausted))
            bd.update({
                'mcq_id': mcq.id,
                'mcq_title': mcq.title,
                'question': mcq.question,
                'hint': mcq.hint,
                'allow_multiple': mcq.allow_multiple_correct,
                'shuffle': mcq.shuffle_choices,
                'max_attempts': mcq.max_attempts,
                'points': mcq.points,
                'difficulty': mcq.difficulty,
                'choices': [{'id': c.id, 'text': c.text, 'order': c.order} for c in choices],
                'is_solved': grade.is_solved if grade else False,
                'points_earned': grade.points_earned if grade else 0,
                'attempts_used': grade.attempts_count if grade else 0,
                'correct_ids': [c.id for c in choices if c.is_correct] if reveal else [],
                'explanation': mcq.explanation if reveal else '',
            })

        elif block.block_type == 'fill_blank' and block.fill_blank_exercise:
            ex = block.fill_blank_exercise
            gr = FillBlankGrade.objects.filter(student=user, exercise=ex).first() if user and not preview else None
            bd.update({
                'fill_blank_id': ex.id, 'title': ex.title,
                'instructions': ex.instructions,
                'text_rendered': ex.text_with_blanks,
                'blank_count': len(ex.answers or {}),
                'points': ex.points, 'difficulty': ex.difficulty,
                'hint': ex.hint, 'max_attempts': ex.max_attempts,
                'is_solved': gr.is_solved if gr else False,
                'attempts_used': gr.attempts_count if gr else 0,
            })

        elif block.block_type == 'true_false' and block.true_false_exercise:
            ex = block.true_false_exercise
            gr = TrueFalseGrade.objects.filter(student=user, exercise=ex).first() if user and not preview else None
            stmts = [{'statement': s.get('statement', ''), 'is_true': s.get('is_true', True)} for s in (ex.statements or [])]
            bd.update({
                'true_false_id': ex.id, 'title': ex.title,
                'statements': stmts,
                'points_per_statement': ex.points_per_statement,
                'difficulty': ex.difficulty, 'hint': ex.hint,
                'is_solved': gr.is_solved if gr else False,
                'attempts_used': gr.attempts_count if gr else 0,
            })

        elif block.block_type == 'code_order' and block.code_order_exercise:
            ex = block.code_order_exercise
            gr = CodeOrderGrade.objects.filter(student=user, exercise=ex).first() if user and not preview else None
            all_lines = list(ex.correct_order) + list(ex.distractor_lines or [])
            indices = list(range(len(all_lines)))
            rng = random.Random(user_id + ex.id)
            rng.shuffle(indices)
            shuffled = [all_lines[i] for i in indices]
            bd.update({
                'code_order_id': ex.id, 'title': ex.title,
                'instructions': ex.instructions,
                'shuffled_lines': shuffled,
                'shuffled_indices_json': json.dumps(indices),
                'points': ex.points, 'difficulty': ex.difficulty,
                'hint': ex.hint, 'max_attempts': ex.max_attempts,
                'is_solved': gr.is_solved if gr else False,
                'attempts_used': gr.attempts_count if gr else 0,
            })

        elif block.block_type == 'matching' and block.matching_exercise:
            ex = block.matching_exercise
            gr = MatchingGrade.objects.filter(student=user, exercise=ex).first() if user and not preview else None
            pairs = ex.pairs or []
            left = [p.get('left', '') for p in pairs]
            right = [p.get('right', '') for p in pairs]
            indices = list(range(len(right)))
            rng = random.Random(user_id + ex.id + 1)
            rng.shuffle(indices)
            shuffled_right = [right[i] for i in indices]
            bd.update({
                'matching_id': ex.id, 'title': ex.title,
                'instructions': ex.instructions,
                'left_items': left, 'right_items': shuffled_right,
                'right_indices': list(range(len(pairs))),
                'pairs': pairs,
                'points': ex.points, 'difficulty': ex.difficulty,
                'hint': ex.hint,
                'is_solved': gr.is_solved if gr else False,
                'attempts_used': gr.attempts_count if gr else 0,
            })

        elif block.block_type == 'short_answer' and block.short_answer_exercise:
            ex = block.short_answer_exercise
            gr = ShortAnswerGrade.objects.filter(student=user, exercise=ex).first() if user and not preview else None
            bd.update({
                'short_answer_id': ex.id, 'title': ex.title,
                'question': ex.question,
                'points': ex.points, 'difficulty': ex.difficulty,
                'hint': ex.hint, 'max_attempts': ex.max_attempts,
                'is_code_answer': ex.is_code_answer,
                'is_solved': gr.is_solved if gr else False,
                'attempts_used': gr.attempts_count if gr else 0,
            })

        elif block.block_type == 'grouped_exercise' and block.grouped_exercise:
            group = block.grouped_exercise
            questions = []
            for idx, q in enumerate(group.questions or []):
                qt = q.get('question_type')
                qid = q.get('exercise_id')
                label = q.get('label', f'Q{idx + 1}')
                if qt == 'qcm':
                    ex = MCQExercise.objects.filter(id=qid).first()
                    if not ex:
                        continue
                    gr = MCQGrade.objects.filter(student=user, exercise=ex).first() if user and not preview else None
                    choices = list(ex.choices.order_by('order'))
                    reveal = preview or (gr and (gr.is_solved or (ex.max_attempts > 0 and gr.attempts_count >= ex.max_attempts)))
                    questions.append({
                        'type': 'mcq', 'label': label,
                        'mcq_id': ex.id, 'mcq_title': ex.title, 'question': ex.question,
                        'hint': ex.hint, 'allow_multiple': ex.allow_multiple_correct,
                        'shuffle': ex.shuffle_choices, 'max_attempts': ex.max_attempts,
                        'points': ex.points, 'difficulty': ex.difficulty,
                        'choices': [{'id': c.id, 'text': c.text, 'order': c.order} for c in choices],
                        'is_solved': gr.is_solved if gr else False,
                        'points_earned': gr.points_earned if gr else 0,
                        'attempts_used': gr.attempts_count if gr else 0,
                        'correct_ids': [c.id for c in choices if c.is_correct] if reveal else [],
                        'explanation': ex.explanation if reveal else '',
                    })
                elif qt == 'fill_blank':
                    ex = FillBlankExercise.objects.filter(id=qid).first()
                    if not ex:
                        continue
                    gr = FillBlankGrade.objects.filter(student=user, exercise=ex).first() if user and not preview else None
                    questions.append({
                        'type': 'fill_blank', 'label': label,
                        'fill_blank_id': ex.id, 'title': ex.title,
                        'instructions': ex.instructions,
                        'text_with_blanks': ex.text_with_blanks,
                        'blank_count': len(ex.answers or {}),
                        'points': ex.points, 'difficulty': ex.difficulty,
                        'hint': ex.hint, 'max_attempts': ex.max_attempts,
                        'is_solved': gr.is_solved if gr else False,
                        'attempts_used': gr.attempts_count if gr else 0,
                    })
                elif qt == 'true_false':
                    ex = TrueFalseExercise.objects.filter(id=qid).first()
                    if not ex:
                        continue
                    gr = TrueFalseGrade.objects.filter(student=user, exercise=ex).first() if user and not preview else None
                    questions.append({
                        'type': 'true_false', 'label': label,
                        'true_false_id': ex.id, 'title': ex.title,
                        'statements': ex.statements or [],
                        'points_per_statement': ex.points_per_statement,
                        'difficulty': ex.difficulty, 'hint': ex.hint,
                        'is_solved': gr.is_solved if gr else False,
                        'attempts_used': gr.attempts_count if gr else 0,
                    })
                elif qt == 'short_answer':
                    ex = ShortAnswerExercise.objects.filter(id=qid).first()
                    if not ex:
                        continue
                    gr = ShortAnswerGrade.objects.filter(student=user, exercise=ex).first() if user and not preview else None
                    questions.append({
                        'type': 'short_answer', 'label': label,
                        'short_answer_id': ex.id, 'title': ex.title,
                        'question': ex.question,
                        'points': ex.points, 'difficulty': ex.difficulty,
                        'hint': ex.hint, 'max_attempts': ex.max_attempts,
                        'is_code_answer': ex.is_code_answer,
                        'is_solved': gr.is_solved if gr else False,
                        'attempts_used': gr.attempts_count if gr else 0,
                    })
            bd.update({
                'grouped_exercise_id': group.id,
                'group_title': group.title,
                'group_instructions': group.instructions,
                'question_type': group.question_type,
                'questions': questions,
            })

        result.append(bd)

    return result


def build_legacy_code_exercises(*, course_lesson=None, formation_lesson=None, user=None):
    """Legacy CodeExercise list when no LessonBlocks exist."""
    filter_kw = (
        {'course_lesson': course_lesson}
        if course_lesson else
        {'formation_lesson': formation_lesson}
    )
    raw_exs = CodeExercise.objects.filter(is_active=True, **filter_kw).order_by('order')
    if not raw_exs.exists():
        return []

    solved_ids = set()
    if user:
        solved_ids = set(
            StudentCodeSubmission.objects.filter(
                student=user, is_correct=True, exercise__in=raw_exs,
            ).values_list('exercise_id', flat=True)
        )

    data = []
    for ex in raw_exs:
        tc_b64 = base64.b64encode(ex.test_code.encode()).decode() if ex.test_code else ''
        data.append({
            'id': ex.id,
            'title': ex.title,
            'instructions': ex.instructions,
            'starter_code': ex.starter_code,
            'expected_output': ex.expected_output,
            'evaluation_mode': ex.evaluation_mode,
            'difficulty': ex.difficulty,
            'hint': ex.hint,
            'max_attempts': ex.max_attempts,
            'points': ex.points,
            'order': ex.order,
            'test_code_b64': tc_b64,
            'is_solved': ex.id in solved_ids,
        })
    return data
