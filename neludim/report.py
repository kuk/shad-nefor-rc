
from dataclasses import dataclass
from collections import defaultdict
from itertools import groupby
from copy import deepcopy

from .text import user_mention
from .const import (
    CONFIRM_STATE,
    FAIL_STATE,

    GREAT_SCORE,
    OK_SCORE,
    BAD_SCORE,
)


def report_text(lines, html=False):
    text = '\n'.join(lines) or '∅'

    if html:
        return '<pre>%s</pre>' % text

    return text


#######
#
#   MATCH REPORT
#
#######


@dataclass
class MatchReportRecord:
    user_id: int
    no_partner: bool
    state: str
    feedback_score: str


def gen_match_report(contacts):
    group_contacts = defaultdict(list)
    for contact in contacts:
        user_id, partner_user_id = contact.user_id, contact.partner_user_id
        if partner_user_id and user_id > partner_user_id:
            user_id, partner_user_id = partner_user_id, user_id
        group_contacts[user_id, partner_user_id].append(contact)

    def key(group):
        no_partner = len(group) == 1
        has_feedback = any(_.feedback_score for _ in group)
        states = {_.state for _ in group if _.state}

        if states:
            has_state = True
            state_order = (
                0 if CONFIRM_STATE in states
                else 1
            )
        else:
            has_state = False
            state_order = None

        return (
            no_partner,
            not has_feedback,
            not has_state,
            state_order
        )

    for group in sorted(group_contacts.values(), key=key):
        for contact in group:
            yield MatchReportRecord(
                user_id=contact.user_id,
                no_partner=len(group) == 1,
                state=contact.state,
                feedback_score=contact.feedback_score
            )


def format_match_report(records, id_users):
    for index, record in enumerate(records):
        user = id_users[record.user_id]
        mention = user_mention(user)

        state, feedback_score, corner = '   '

        if record.no_partner:
            state = 'NP'
        elif record.state:
            state = {
                CONFIRM_STATE: 'C',
                FAIL_STATE: 'F!',
            }[record.state]

        if record.feedback_score:
            feedback_score = {
                GREAT_SCORE: 'G',
                OK_SCORE: 'OK',
                BAD_SCORE: 'B!',
            }[record.feedback_score]

        if state != 'NP':
            corner = '╭╰'[index % 2]

        yield f'{corner} {state:<2} {feedback_score:>2} {mention}'


######
#
#   WEEKS REPORT
#
####


@dataclass
class WeeksReportRecord:
    week_index: int

    total: int = 0
    first_time: int = 0
    no_partner: int = 0

    confirm_state: int = 0
    fail_state: int = 0
    none_state: int = 0

    great_feedback: int = 0
    ok_feedback: int = 0
    bad_feedback: int = 0
    none_feedback: int = 0


def propogate_contact_states(contacts):
    group_contacts = defaultdict(list)
    for contact in contacts:
        if contact.partner_user_id:
            user_id, partner_user_id = contact.user_id, contact.partner_user_id
            if user_id > partner_user_id:
                user_id, partner_user_id = partner_user_id, user_id
            group_contacts[user_id, partner_user_id].append(contact)

    for group in group_contacts.values():
        states = {_.state for _ in group if _.state}

        if states:
            if FAIL_STATE in states and CONFIRM_STATE in states:
                state = None
            elif CONFIRM_STATE in states:
                state = CONFIRM_STATE
            elif FAIL_STATE in states:
                state = FAIL_STATE
        else:
            state = None

        for contact in group:
            contact.state = state


def gen_weeks_report(contacts):
    seen_user_ids = set()

    contacts = sorted(contacts, key=lambda _: _.week_index)
    for week_index, week_contacts in groupby(contacts, key=lambda _: _.week_index):
        week_contacts = deepcopy(list(week_contacts))
        propogate_contact_states(week_contacts)

        user_ids = set()
        no_partner_user_ids = set()
        user_id_states = {}
        user_id_feedback_scores = {}
        for contact in week_contacts:
            user_ids.add(contact.user_id)
            if not contact.partner_user_id:
                no_partner_user_ids.add(contact.user_id)
            else:
                if contact.state:
                    user_id_states[contact.user_id] = contact.state
                if contact.feedback_score:
                    user_id_feedback_scores[contact.user_id] = contact.feedback_score

        record = WeeksReportRecord(week_index)
        for user_id in user_ids:
            record.total += 1
            if user_id not in seen_user_ids:
                record.first_time += 1

            if user_id in no_partner_user_ids:
                record.no_partner += 1
            else:

                state = user_id_states.get(user_id)
                if state is None:
                    record.none_state += 1
                elif state == CONFIRM_STATE:
                    record.confirm_state += 1
                elif state == FAIL_STATE:
                    record.fail_state += 1

                feedback_score = user_id_feedback_scores.get(user_id)
                if state == CONFIRM_STATE:
                    if feedback_score is None:
                        record.none_feedback += 1
                    elif feedback_score == GREAT_SCORE:
                        record.great_feedback += 1
                    elif feedback_score == OK_SCORE:
                        record.ok_feedback += 1
                    elif feedback_score == BAD_SCORE:
                        record.bad_feedback += 1

        seen_user_ids.update(user_ids)
        yield record


def format_weeks_report(records):
    for index, _ in enumerate(records):
        if index % 12 == 0:
            yield ' T FT NP   C F!  ∅   +  -  ∅'

        yield (
            f'{_.total:>2} {_.first_time:>2} {_.no_partner:>2}  '
            f'{_.confirm_state:>2} {_.fail_state:>2} {_.none_state:>2}  '
            f'{_.great_feedback + _.ok_feedback:>2} {_.bad_feedback:>2} {_.none_feedback:>2}'
        )
