"""
Copyright ©2018. The Regents of the University of California (Regents). All Rights Reserved.

Permission to use, copy, modify, and distribute this software and its documentation
for educational, research, and not-for-profit purposes, without fee and without a
signed licensing agreement, is hereby granted, provided that the above copyright
notice, this paragraph and the following two paragraphs appear in all copies,
modifications, and distributions.

Contact The Office of Technology Licensing, UC Berkeley, 2150 Shattuck Avenue,
Suite 510, Berkeley, CA 94720-1620, (510) 643-7201, otl@berkeley.edu,
http://ipira.berkeley.edu/industry-info for commercial licensing opportunities.

IN NO EVENT SHALL REGENTS BE LIABLE TO ANY PARTY FOR DIRECT, INDIRECT, SPECIAL,
INCIDENTAL, OR CONSEQUENTIAL DAMAGES, INCLUDING LOST PROFITS, ARISING OUT OF
THE USE OF THIS SOFTWARE AND ITS DOCUMENTATION, EVEN IF REGENTS HAS BEEN ADVISED
OF THE POSSIBILITY OF SUCH DAMAGE.

REGENTS SPECIFICALLY DISCLAIMS ANY WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE. THE
SOFTWARE AND ACCOMPANYING DOCUMENTATION, IF ANY, PROVIDED HEREUNDER IS PROVIDED
"AS IS". REGENTS HAS NO OBLIGATION TO PROVIDE MAINTENANCE, SUPPORT, UPDATES,
ENHANCEMENTS, OR MODIFICATIONS.
"""


from boac import db, std_commit
from boac.lib.berkeley import BERKELEY_DEPT_NAME_TO_CODE
from boac.models.athletics import Athletics
from boac.models.authorized_user import AuthorizedUser
from boac.models.cohort_filter import CohortFilter
from boac.models.student import Student
from boac.models.student_group import StudentGroup
from boac.models.university_dept import UniversityDept
# Models below are included so that db.create_all will find them.
from boac.models.alert import Alert # noqa
from boac.models.db_relationships import AlertView, cohort_filter_owners, student_athletes, UniversityDeptMember  # noqa
from boac.models.job_progress import JobProgress # noqa
from boac.models.json_cache import JsonCache # noqa
from boac.models.normalized_cache_student import NormalizedCacheStudent # noqa
from boac.models.normalized_cache_student_major import NormalizedCacheStudentMajor # noqa
from flask import current_app as app
from sqlalchemy.sql import text


_test_users = [
    ['2040', True],
    ['53791', True],
    ['95509', True],
    ['177473', True],
    ['1133399', True],
    ['211159', True],
    ['242881', True],
    ['1022796', False],
    ['1015674', False],
    ['1049291', True],
    ['1081940', False],
    ['90412', True],
    ['6446', False],
]

_users_per_dept = {
    'COENG': [
        {
            'uid': '1022796',
            'is_advisor': False,
            'is_director': True,
        },
    ],
    'UWASC': [
        {
            'uid': '1081940',
            'is_advisor': True,
            'is_director': False,
        },
        {
            'uid': '90412',
            'is_advisor': False,
            'is_director': True,
        },
        {
            'uid': '6446',
            'is_advisor': True,
            'is_director': True,
        },
    ],
}

football_defensive_backs = {
    'group_code': 'MFB-DB',
    'group_name': 'Football, Defensive Backs',
    'team_code': 'FBM',
    'team_name': 'Football',
}
football_defensive_line = {
    'group_code': 'MFB-DL',
    'group_name': 'Football, Defensive Line',
    'team_code': 'FBM',
    'team_name': 'Football',
}
womens_field_hockey = {
    'group_code': 'WFH',
    'group_name': 'Women\'s Field Hockey',
    'team_code': 'FHW',
    'team_name': 'Women\'s Field Hockey',
}
mens_baseball = {
    'group_code': 'MBB',
    'group_name': 'Men\'s Baseball',
    'team_code': 'BAM',
    'team_name': 'Men\'s Baseball',
}
mens_tennis = {
    'group_code': 'MTE',
    'group_name': 'Men\'s Tennis',
    'team_code': 'TNM',
    'team_name': 'Men\'s Tennis',
}
womens_tennis = {
    'group_code': 'WTE',
    'group_name': 'Women\'s Tennis',
    'team_code': 'TNW',
    'team_name': 'Women\'s Tennis',
}


def clear():
    with open(app.config['BASE_DIR'] + '/scripts/db/drop_schema.sql', 'r') as ddlfile:
        ddltext = ddlfile.read()
    db.session().execute(text(ddltext))
    std_commit()


def load(cohort_test_data=False):
    load_schemas()
    load_development_data()
    if cohort_test_data:
        load_student_athletes()
        create_cohorts()
    return db


def load_schemas():
    """Create DB schema from SQL file."""
    with open(app.config['BASE_DIR'] + '/scripts/db/schema.sql', 'r') as ddlfile:
        ddltext = ddlfile.read()
    db.session().execute(text(ddltext))
    std_commit()


def load_development_data():
    for name, code in BERKELEY_DEPT_NAME_TO_CODE.items():
        UniversityDept.create(code, name)
    for test_user in _test_users:
        # This script can be run more than once. Do not create user if s/he exists in BOAC db.
        user = AuthorizedUser.find_by_uid(uid=test_user[0])
        if not user:
            user = AuthorizedUser(uid=test_user[0], is_admin=test_user[1])
            db.session.add(user)
    for dept_code, users in _users_per_dept.items():
        university_dept = UniversityDept.find_by_dept_code(dept_code)
        for user in users:
            authorized_user = AuthorizedUser.find_by_uid(user['uid'])
            UniversityDeptMember.create_membership(
                university_dept,
                authorized_user,
                user['is_advisor'],
                user['is_director'],
            )
    std_commit(allow_test_environment=True)


def create_team_group(t):
    athletics = Athletics(
        group_code=t['group_code'],
        group_name=t['group_name'],
        team_code=t['team_code'],
        team_name=t['team_name'],
    )
    db.session.add(athletics)
    return athletics


def create_student(sid, uid, first_name, last_name, team_groups, gpa, level, units, majors, in_intensive_cohort=False):
    student = Student(
        sid=sid,
        uid=uid,
        first_name=first_name,
        last_name=last_name,
        in_intensive_cohort=in_intensive_cohort,
    )
    db.session.add(student)
    for team_group in team_groups:
        team_group.athletes.append(student)
    NormalizedCacheStudent.update_profile(sid, gpa=gpa, level=level, units=units)
    NormalizedCacheStudentMajor.update_majors(sid, majors)
    return student


def load_student_athletes():
    fdb = create_team_group(football_defensive_backs)
    fdl = create_team_group(football_defensive_line)
    mbb = create_team_group(mens_baseball)
    mt = create_team_group(mens_tennis)
    wfh = create_team_group(womens_field_hockey)
    wt = create_team_group(womens_tennis)
    # Some students are on teams and some are not
    deborah = create_student(
        uid='61889',
        sid='11667051',
        first_name='Deborah',
        last_name='Davies',
        team_groups=[wfh, wt],
        gpa=None,
        level=None,
        units=0,
        majors=['History BA'],
        in_intensive_cohort=True,
    )
    create_student(
        uid='1022796',
        sid='8901234567',
        first_name='John David',
        last_name='Crossman',
        team_groups=[],
        gpa='1.85',
        level='Freshman',
        units=12,
        majors=['Economics BA'],
        in_intensive_cohort=True,
    )
    create_student(
        uid='98765',
        sid='2345678901',
        first_name='Dave',
        last_name='Doolittle',
        team_groups=[fdb, fdl],
        gpa='3.495',
        level='Junior',
        units=34,
        majors=['Chemistry BS'],
    )
    paul_kerschen = create_student(
        uid='242881',
        sid='3456789012',
        first_name='Paul',
        last_name='Kerschen',
        team_groups=[fdl],
        gpa='3.005',
        level='Junior',
        units=70,
        majors=['English BA', 'Political Economy BA'],
        in_intensive_cohort=True,
    )
    sandeep = create_student(
        uid='1133399',
        sid='5678901234',
        first_name='Sandeep',
        last_name='Jayaprakash',
        team_groups=[fdb, fdl, mt],
        gpa='3.501',
        level='Senior',
        units=102,
        majors=['Letters & Sci Undeclared UG'],
    )
    paul_farestveit = create_student(
        uid='1049291',
        sid='7890123456',
        first_name='Paul',
        last_name='Farestveit',
        team_groups=[mbb],
        gpa='3.90',
        level='Senior',
        units=110,
        majors=['History BA'],
        in_intensive_cohort=True,
    )
    schlemiel = create_student(
        uid='211159',
        sid='890127492',
        first_name='Siegfried',
        last_name='Schlemiel',
        # 'A mug is a mug in everything.' - Colonel Harrington
        team_groups=[fdb, fdl, mt, wfh, wt],
        gpa='0.40',
        level='Sophomore',
        units=8,
        majors=['Mathematics'],
        in_intensive_cohort=True,
    )
    schlemiel.is_active_asc = False
    schlemiel.status_asc = 'Trouble'
    db.session.merge(schlemiel)

    # Create empty default group for all users.
    for user in AuthorizedUser.query.all():
        StudentGroup.create(user.id, 'My Students')

    advisor = AuthorizedUser.find_by_uid('6446')
    group = StudentGroup.create(advisor.id, 'Cool Kids')
    for student in [paul_kerschen, sandeep, deborah, paul_farestveit]:
        StudentGroup.add_student(group.id, student.sid)
    std_commit(allow_test_environment=True)


def create_cohorts():
    # Oliver's cohorts
    CohortFilter.create(uid='2040', label='All sports', group_codes=['MFB-DL', 'WFH'])
    CohortFilter.create(uid='2040', label='Football, Defense', group_codes=['MFB-DB', 'MFB-DL'])
    CohortFilter.create(uid='2040', label='Field Hockey', group_codes=['WFH'])
    # Sandeep's cohorts
    CohortFilter.create(uid='1133399', label='Defense Backs, Inactive', group_codes=['MFB-DB'], is_inactive_asc=True)
    CohortFilter.create(uid='1133399', label='Defense Backs, Active', group_codes=['MFB-DB'], is_inactive_asc=False)
    CohortFilter.create(uid='1133399', label='Defense Backs, All', group_codes=['MFB-DB'])
    CohortFilter.create(uid='1133399', label='Undeclared students', majors=['Undeclared'], is_inactive_asc=False)
    CohortFilter.create(uid='1133399', label='All sports', group_codes=['MFB-DL', 'WFH'], is_inactive_asc=False)
    std_commit(allow_test_environment=True)


if __name__ == '__main__':
    import boac.factory
    boac.factory.create_app()
    load()
