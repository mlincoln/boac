<template>
  <div>
    <b-table
      :borderless="true"
      :fields="fields"
      :items="admittedStudents"
      :no-sort-reset="true"
      :small="true"
      :sort-by.sync="sortBy"
      :sort-compare="sortCompare"
      :sort-desc.sync="sortDescending"
      stacked="md"
      thead-class="sortable-table-header text-nowrap"
    >
      <template v-slot:cell(curated)="row">
        <CuratedStudentCheckbox
          domain="admitted_students"
          :student="row.item"
        />
      </template>

      <template v-slot:cell(lastName)="row">
        <span class="sr-only">Admitted student name</span>
        <router-link
          :id="`link-to-admit-${row.item.csEmplId}`"
          :class="{'demo-mode-blur': $currentUser.inDemoMode}"
          :to="admitRoutePath(row.item.csEmplId)"
          v-html="fullName(row.item)"
        ></router-link>
      </template>

      <template v-slot:cell(csEmplId)="row">
        <span class="sr-only">C S I D </span>
        <span :class="{'demo-mode-blur': $currentUser.inDemoMode}">{{ row.item.csEmplId }}</span>
      </template>

      <template v-slot:cell(currentSir)="row">
        <span class="sr-only">S I R</span>
        {{ row.item.currentSir }}
      </template>

      <template v-slot:cell(specialProgramCep)="row">
        <span class="sr-only">C E P</span>
        {{ row.item.specialProgramCep }}
      </template>

      <template v-slot:cell(reentryStatus)="row">
        <span class="sr-only">Re-entry</span>
        {{ row.item.reentryStatus }}
      </template>

      <template v-slot:cell(firstGenerationCollege)="row">
        <span class="sr-only">First generation</span>
        {{ row.item.firstGenerationCollege }}
      </template>

      <template v-slot:cell(urem)="row">
        <span class="sr-only">U R E M</span>
        {{ row.item.urem }}
      </template>

      <template v-slot:cell(applicationFeeWaiverFlag)="row">
        <span class="sr-only">Waiver</span>
        {{ row.item.applicationFeeWaiverFlag }}
      </template>

      <template v-slot:cell(residencyCategory)="row">
        <span class="sr-only">Residency</span>
        {{ row.item.residencyCategory }}
      </template>

      <template v-slot:cell(freshmanOrTransfer)="row">
        <span class="sr-only">Freshman or Transfer</span>
        {{ row.item.freshmanOrTransfer }}
      </template>
    </b-table>
  </div>
</template>

<script>
import Context from '@/mixins/Context'
import CuratedStudentCheckbox from '@/components/curated/dropdown/CuratedStudentCheckbox'
import Util from '@/mixins/Util'

export default {
  name: 'SortableAdmits',
  mixins: [Context, Util],
  components: {CuratedStudentCheckbox},
  props: {
    admittedStudents: {
      required: true,
      type: Array
    }
  },
  data() {
    return {
      fields: undefined,
      sortBy: 'lastName',
      sortDescending: false
    }
  },
  watch: {
    sortBy() {
      this.onChangeSortBy()
    },
    sortDescending() {
      this.onChangeSortBy()
    }
  },
  created() {
    this.fields = [
      {key: 'curated', label: ''},
      {key: 'lastName', label: 'Name', sortable: true},
      {key: 'csEmplId', label: 'CS ID', sortable: true},
      {key: 'currentSir', label: 'SIR', sortable: false},
      {key: 'specialProgramCep', label: 'CEP', sortable: false},
      {key: 'reentryStatus', label: 'Re-entry', sortable: false},
      {key: 'firstGenerationCollege', label: '1st Gen', sortable: false},
      {key: 'urem', label: 'UREM', sortable: false},
      {key: 'applicationFeeWaiverFlag', label: 'Waiver', sortable: false},
      {key: 'residencyCategory', label: 'Residency', sortable: false},
      {key: 'freshmanOrTransfer', label: 'Freshman/Transfer', sortable: false},
    ]
  },
  methods: {
    admitRoutePath(csEmplId) {
      return this.$currentUser.inDemoMode ? `/admit/student/${window.btoa(csEmplId)}` : `/admit/student/${csEmplId}`
    },
    fullName(admit) {
      const lastName = admit.lastName ? `${admit.lastName},` : null
      return this.$_.join(this.$_.remove([lastName, admit.firstName, admit.middleName]), ' ')
    },
    normalizeForSort(value) {
      return this.$_.isString(value) ? value.toLowerCase() : value
    },
    onChangeSortBy() {
      const field = this.$_.find(this.fields, ['key', this.sortBy])
      this.$announcer.polite(`Sorted by ${field.label}${this.sortDescending ? ', descending' : ''}`)
    },
    sortCompare(a, b, sortBy, sortDesc) {
      let aValue = this.normalizeForSort(this.$_.get(a, sortBy))
      let bValue = this.normalizeForSort(this.$_.get(b, sortBy))
      let result = this.sortComparator(aValue, bValue)
      if (result === 0) {
        this.$_.each(['lastName', 'firstName', 'csEmplId'], field => {
          result = this.sortComparator(
            this.normalizeForSort(this.$_.get(a, field)),
            this.normalizeForSort(this.$_.get(b, field))
          )
          // Secondary sort is always ascending
          result *= sortDesc ? -1 : 1
          // Break from loop if comparator result is non-zero
          return result === 0
        })
      }
      return result
    }
  }
}
</script>
