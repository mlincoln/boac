<template>
  <div class="ml-3 mr-3 mt-3">
    <Spinner />
    <div class="d-flex flex-wrap align-items-baseline justify-content-between">
      <h1 id="page-header" class="page-section-header text-nowrap mr-2">Batch Degree Checks</h1>
      <router-link id="manage-degrees-link" to="/degrees">
        <div class="text-nowrap">
          Manage degree checks
        </div>
      </router-link>
    </div>
    <div v-if="!loading">
      <div aria-live="polite" class="font-italic font-size-14 student-count-alerts" role="alert">
        <span
          v-if="!$_.isEmpty(sidsToInclude)"
          id="target-student-count-alert"
          :class="{'has-error': sidsToInclude.length >= 250, 'font-weight-bolder': sidsToInclude.length >= 500}"
        >
          Degree check will be added to {{ pluralize('student record', sidsToInclude.length) }}.
          <span v-if="sidsToInclude.length >= 500">Are you sure?</span>
        </span>
        <span v-if="$_.isEmpty(sidsToInclude) && (addedCohortsEmpty || addedGroupsEmpty)">
          <span v-if="addedCohortsEmpty && !addedGroupsEmpty" id="no-students-per-cohorts-alert">
            There are no students in the {{ pluralize('cohort', addedCohorts.length, {1: ' '}) }}.
          </span>
          <span v-if="!addedCohortsEmpty && addedGroupsEmpty" id="no-students-per-curated-groups-alert">
            There are no students in the {{ pluralize('group', addedCuratedGroups.length, {1: ' '}) }}.
          </span>
          <span v-if="addedCohortsEmpty && addedGroupsEmpty" id="no-students-alert">
            Neither the {{ pluralize('cohort', addedCohorts.length, {1: ' '}) }} nor the {{ pluralize('group', addedCuratedGroups.length, {1: ' '}) }} have students.
          </span>
        </span>
      </div>
      <div class="w-75">
        <label
          for="degree-check-add-student-input"
          class="input-label text mt-1"
        >
          <div class="font-weight-bolder">Student</div>
          <span class="font-size-14">Type or paste a list of SID numbers below. Example: 9999999990, 9999999991</span>
        </label>
        <div class="mb-2">
          <b-form-textarea
            id="degree-check-add-student"
            v-model="textarea"
            :disabled="isBusy"
            aria-label="Type or paste a list of student SID numbers here"
            rows="8"
            max-rows="30"
            @keydown.esc="cancel"
          ></b-form-textarea>
        </div>
        <div class="d-flex justify-content-end">
          <b-btn
            id="degree-check-add-sids-btn"
            class="btn-primary-color-override"
            :disabled="!$_.trim(textarea) || isBusy"
            variant="primary"
            @click="addSids"
          >
            <span v-if="isValidating"><font-awesome icon="spinner" spin /> <span class="pl-1">Adding</span></span>
            <span v-if="!isValidating">Add</span>
          </b-btn>
        </div>
        <div v-for="(addedStudent, index) in addedStudents" :key="addedStudent.sid" class="mb-3">
          <span class="font-weight-bolder pill pill-attachment text-uppercase text-nowrap truncate">
            <span :id="`batch-note-student-${index}`" :class="{'demo-mode-blur': $currentUser.inDemoMode}">{{ addedStudent.label }}</span>
            <b-btn
              :id="`remove-student-from-batch-${index}`"
              variant="link"
              class="p-0"
              :disabled="isSaving"
              @click.prevent="removeStudent(addedStudent)"
            >
              <font-awesome icon="times-circle" class="font-size-24 has-error pl-2" />
              <span class="sr-only">Remove {{ addedStudent.label }} from degree check</span>
            </b-btn>
          </span>
        </div>
      </div>
      <div
        v-if="error || warning"
        :class="{'error-message-container': error, 'warning-message-container': warning}"
        class="alert-box p-3 mt-2 mb-3 w-75"
        v-html="error || warning"
      />
      <div class="mb-2">
        <BatchAddStudentSet
          v-if="$currentUser.myCohorts.length"
          :add-object="addCohort"
          class="w-75"
          :disabled="isSaving"
          header="Cohort"
          :objects="$currentUser.myCohorts"
          object-type="cohort"
          :remove-object="removeCohort"
        />
      </div>
      <div class="mb-2">
        <BatchAddStudentSet
          v-if="$currentUser.myCuratedGroups.length"
          :add-object="addCuratedGroup"
          class="w-75"
          :disabled="isSaving"
          header="Curated Group"
          :objects="$_.filter($currentUser.myCuratedGroups, ['domain', 'default'])"
          object-type="curated"
          :remove-object="removeCuratedGroup"
        />
      </div>
      <div class="mb-3">
        <DegreeTemplatesMenu
          class="w-75"
          :disabled="isSaving"
          :on-select="addTemplate"
        />
      </div>
      <div
        v-if="!isRecalculating && !isValidating && !$_.isEmpty(excludedStudents)"
        class="alert-box warning-message-container p-3 mt-2 mb-3 w-75"
        role="alert"
      >
        <div>{{ excludedStudents.length }} students currently use the {{ selectedTemplate.name }} degree check. The degree check will not be added to their student record.</div>
        <ul class="mt-1 mb-0">
          <li v-for="(student, index) in excludedStudents" :key="index">
            {{ student.firstName }} {{ student.lastName }} ({{ student.sid }})
          </li>
        </ul>
      </div>
      <div class="d-flex justify-content-end pt-2 w-75">
        <b-btn
          id="batch-degree-check-save"
          class="btn-primary-color-override"
          :disabled="isBusy || !selectedTemplate || $_.isEmpty(sidsToInclude)"
          variant="primary"
          @click="save"
        >
          <span v-if="isSaving"><font-awesome class="mr-1" icon="spinner" spin /> Saving</span>
          <span v-if="!isSaving">Save Degree Check</span>
        </b-btn>
        <b-btn
          id="batch-degree-check-cancel"
          class="pr-0"
          :disabled="isBusy"
          variant="link"
          @click.prevent="cancel"
        >
          Cancel
        </b-btn>
      </div>
    </div>
  </div>
</template>

<script>
import BatchAddStudentSet from '@/components/util/BatchAddStudentSet'
import Context from '@/mixins/Context'
import DegreeEditSession from '@/mixins/DegreeEditSession'
import DegreeTemplatesMenu from '@/components/degree/DegreeTemplatesMenu'
import Loading from '@/mixins/Loading'
import Spinner from '@/components/util/Spinner'
import StudentAggregator from '@/mixins/StudentAggregator'
import Util from '@/mixins/Util'
import Validator from '@/mixins/Validator'
import {createBatchDegreeCheck, getStudents} from '@/api/degree'
import {getStudentsBySids} from '@/api/student'

export default {
  name: 'BatchDegreeCheck',
  components: {
    BatchAddStudentSet,
    DegreeTemplatesMenu,
    Spinner
  },
  mixins: [Context, DegreeEditSession, Loading, StudentAggregator, Util, Validator],
  data: () => ({
    addedCohorts: [],
    addedCuratedGroups: [],
    addedStudents: [],
    error: undefined,
    excludedStudents: [],
    isSaving: false,
    isValidating: false,
    selectedTemplate: undefined,
    textarea: undefined,
    warning: undefined
  }),
  computed: {
    addedCohortsEmpty() {
      return this.addedCohorts.length && this.$_.every(this.addedCohorts, {'totalStudentCount': 0})
    },
    addedGroupsEmpty() {
      return this.addedCuratedGroups.length && this.$_.every(this.addedCuratedGroups, {'totalStudentCount': 0})
    },
    addedSids() {
      return this.$_.map(this.addedStudents, 'sid')
    },
    isBusy() {
      return this.isSaving || this.isValidating || this.isRecalculating
    },
    sidsToInclude() {
      const sidsToExclude = this.$_.map(this.excludedStudents, 'sid')
      return this.$_.difference(this.distinctSids, sidsToExclude)
    }
  },
  watch: {
    selectedTemplate(newValue) {
      this.findStudentsWithDegreeCheck(newValue, this.distinctSids)
    },
    distinctSids(newValue) {
      this.findStudentsWithDegreeCheck(this.selectedTemplate, newValue)
    }
  },
  mounted() {
    this.loaded('Batch degree checks loaded')
  },
  methods: {
    addCohort(cohort) {
      this.clearErrors()
      this.addedCohorts.push(cohort)
      this.recalculateStudentCount(this.addedSids, this.addedCohorts, this.addedCuratedGroups)
    },
    addCuratedGroup(curatedGroup) {
      this.clearErrors()
      this.addedCuratedGroups.push(curatedGroup)
      this.recalculateStudentCount(this.addedSids, this.addedCohorts, this.addedCuratedGroups)
    },
    addSids() {
      return new Promise((resolve, reject) => {
        this.isValidating = true
        const sids = this.validateSids(this.textarea)
        if (sids) {
          const uniqueSids = this.$_.uniq(sids)
          getStudentsBySids(uniqueSids).then(students => {
            this.addStudents(students)
            const notFound = this.$_.difference(uniqueSids, this.$_.map(students, 'sid'))
            if (notFound.length === 1) {
              this.warning = `Student ${notFound[0]} not found.`
              this.$announcer.polite(this.warning)
            } else if (notFound.length > 1) {
              this.warning = `${notFound.length} students not found: <ul class="mt-1 mb-0"><li>${this.$_.join(notFound, '</li><li>')}</li></ul>`
              this.$announcer.polite(`${notFound.length} student IDs not found: ${this.oxfordJoin(notFound)}`)
            }
            this.isValidating = false
            this.textarea = undefined
            resolve()
          })
        } else {
          if (this.error) {
            this.$announcer.polite(`Error: ${this.error}`)
          } else if (this.warning) {
            this.$announcer.polite(`Warning: ${this.warning}`)
          }
          this.$nextTick(() => this.isValidating = false)
          reject()
        }
      })
    },
    addStudents(students) {
      if (students && students.length) {
        this.addedStudents.push(...students)
        this.recalculateStudentCount(this.addedSids, this.addedCohorts, this.addedCuratedGroups).then( () => {
          const obj = students.length === 1 ? `${students[0].label}` : this.pluralize('student', students.length)
          this.$announcer.polite(`${obj} added to degree check`)
        })
      }
      this.$putFocusNextTick('degree-check-add-student-input')
    },
    addTemplate(template) {
      this.selectedTemplate = template
      this.findStudentsWithDegreeCheck()
    },
    cancel() {
      this.$announcer.polite('Canceled. Nothing saved.')
      this.$router.push('/degrees')
    },
    findStudentsWithDegreeCheck(selectedTemplate, sids) {
      if (this.$_.get(selectedTemplate, 'id') && !this.$_.isEmpty(sids)) {
        this.isValidating = true
        getStudents(selectedTemplate.id, sids).then(students => {
          this.excludedStudents = students
          this.isValidating = false
        })
      } else {
        this.excludedStudents = []
      }
    },
    removeCohort(cohort) {
      const index = this.$_.indexOf(this.addedCohorts, cohort)
      if (index !== -1) {
        this.addedCohorts.splice(index, 1)
        this.recalculateStudentCount(this.addedSids, this.addedCohorts, this.addedCuratedGroups)
      }
    },
    removeCuratedGroup(curatedGroup) {
      const index = this.$_.indexOf(this.addedCuratedGroups, curatedGroup)
      if (index !== -1) {
        this.addedCuratedGroups.splice(index, 1)
        this.recalculateStudentCount(this.addedSids, this.addedCohorts, this.addedCuratedGroups)
      }
    },
    removeStudent(student) {
      const index = this.$_.indexOf(this.addedStudents, student)
      if (index !== -1) {
        this.addedStudents.splice(index, 1)
        this.recalculateStudentCount(this.addedSids, this.addedCohorts, this.addedCuratedGroups).then(() => this.$announcer.polite(`${student.label} removed`))
      }
    },
    save() {
      this.isSaving = true
      this.$announcer.polite('Saving.')
      createBatchDegreeCheck(this.sidsToInclude, this.$_.get(this.selectedTemplate, 'id')).then(() => {
        this.$nextTick(() => {
          this.$router.push({
            path: '/degrees',
            query: {
              m: `Degree check ${this.selectedTemplate.name} added to ${this.pluralize('student profile', this.sidsToInclude.length)}.`
            }
          })
        })
      }).finally(() => {
        this.isSaving = false
      })
    }
  }
}
</script>

<style scoped>
.student-count-alerts {
  line-height: 1.2rem;
  min-height: 1.2rem;
}
</style>
