<template>
  <b-card
    :id="`sortable-${keyword}-${group.id}`"
    body-class="p-0"
    :border-variant="isFetching || openAndLoaded ? 'primary' : 'light'"
    class="mr-3 sortable-group"
    :class="{
      'bg-pale-blue': isFetching || openAndLoaded,
      'border-0': !isFetching && !openAndLoaded
    }"
  >
    <b-card-header class="bg-transparent border-0 pl-1" :class="{'p-0': compact}">
      <b-button
        :id="`sortable-${keyword}-${group.id}-toggle`"
        v-b-toggle="`sortable-${keyword}-${group.id}`"
        block
        class="border-0"
        :class="{'shadow-none': !isOpen && !buttonHasFocus}"
        :pressed="null"
        variant="link"
        @click.prevent="fetchStudents"
        @focus="buttonHasFocus = true"
        @blur="buttonHasFocus = false"
      >
        <div class="d-flex justify-content-between">
          <div class="align-items-start d-flex">
            <div class="caret pale-blue pr-4">
              <font-awesome v-if="isFetching" icon="spinner" spin />
              <font-awesome v-if="!isFetching" :icon="isOpen ? 'caret-down' : 'caret-right'" />
            </div>
            <h3 class="page-section-header-sub text-wrap">
              <span class="sr-only">{{ `${isOpen ? 'Hide' : 'Show'} details for ${groupTypeName} ` }}</span>
              {{ group.name }}
              (<span :id="`sortable-${keyword}-${group.id}-total-student-count`">{{ group.totalStudentCount }}</span>
              <span class="sr-only">&nbsp;students</span>)
            </h3>
          </div>
          <div class="count align-items-center d-flex justify-content-end">
            <div v-if="!compact" class="pr-2 sortable-table-header">
              Total Alerts:
            </div>
            <div
              v-if="!group.alertCount"
              class="pill-alerts pill-alerts-zero"
              :aria-label="`No issues for ${groupTypeName} '${group.name}'`"
            >
              0
            </div>
            <div
              v-if="group.alertCount"
              class="font-weight-normal pill-alerts pill-alerts-nonzero mb-1 pl-2 pr-2"
              :aria-label="`${group.alertCount} alerts for ${groupTypeName} '${group.name}'`"
            >
              {{ group.alertCount }}
            </div>
          </div>
        </div>
      </b-button>
    </b-card-header>
    <b-collapse
      :id="`sortable-${keyword}-${group.id}`"
      :aria-expanded="openAndLoaded"
      class="mr-3"
    >
      <div v-if="$_.size(studentsWithAlerts)">
        <div v-if="!compact && $_.size(studentsWithAlerts) === 50" :id="`sortable-${keyword}-${group.id}-alert-limited`" class="px-3">
          Showing 50 students with a high number of alerts.
          <router-link
            :id="`sortable-${keyword}-${group.id}-alert-limited-view-all`"
            :to="getRoutePath(group)"
          >
            View all {{ group.totalStudentCount }} students in {{ groupTypeName }} "{{ group.name }}"
          </router-link>
        </div>
        <div class="pt-4">
          <SortableStudents
            domain="default"
            :students="studentsWithAlerts"
            :options="sortableGroupOptions"
          />
        </div>
      </div>
      <div v-if="openAndLoaded" class="mb-3 ml-3">
        <router-link
          :id="`sortable-${keyword}-${group.id}-view-all`"
          :to="getRoutePath(group)"
        >
          <span v-if="group.totalStudentCount">
            View {{ pluralize('student', group.totalStudentCount, {1: 'the one', 'other': `all ${group.totalStudentCount}`}) }}
            in {{ groupTypeName }} "{{ group.name }}"
          </span>
          <div v-if="!group.totalStudentCount" class="pt-3">
            {{ $_.capitalize(groupTypeName) }} "{{ group.name }}" has 0 students
          </div>
        </router-link>
      </div>
    </b-collapse>
  </b-card>
</template>

<script>
import Context from '@/mixins/Context'
import SortableStudents from '@/components/search/SortableStudents'
import Util from '@/mixins/Util'
import {getStudentsWithAlerts as getCohortStudentsWithAlerts} from '@/api/cohort'
import {getStudentsWithAlerts as getCuratedStudentsWithAlerts} from '@/api/curated'

export default {
  name: 'SortableGroup',
  components: {SortableStudents},
  mixins: [Context, Util],
  props: {
    compact: {
      type: Boolean
    },
    group: {
      required: true,
      type: Object
    },
    isCohort: {
      required: true,
      type: Boolean
    }
  },
  data: () => ({
    buttonHasFocus: false,
    groupTypeName: undefined,
    isFetching: undefined,
    isOpen: undefined,
    keyword: undefined,
    studentsWithAlerts: undefined
  }),
  computed: {
    openAndLoaded: {
      get: function() {
        return this.isOpen && !this.isFetching
      },
      set: function(value) {
        this.isOpen = value
      }
    },
    sortableGroupOptions() {
      return {
        compact: this.compact,
        includeCuratedCheckbox: false,
        reverse: true,
        sortBy: 'alertCount'
      }
    }
  },
  mounted() {
    this.keyword = this.isCohort ? 'cohort' : 'curated'
    this.groupTypeName = this.isCohort ? 'cohort' : 'curated group'
  },
  methods: {
    fetchStudents() {
      this.isOpen = !this.isOpen
      if (this.$_.isNil(this.studentsWithAlerts)) {
        this.isFetching = true
        const apiCall = this.isCohort ? getCohortStudentsWithAlerts : getCuratedStudentsWithAlerts
        apiCall(this.group.id).then(students => {
          this.studentsWithAlerts = students
          this.isFetching = false
          this.$announcer.polite(`Loaded students with alerts who are in ${this.groupTypeName} ${this.group.name}`)
        })
      }
    },
    getRoutePath(group) {
      return `/${this.keyword}/${group.id}?domain=${group.domain}`
    }
  }
}
</script>

<style scoped>
.bg-pale-blue {
  background-color: #f3fbff;
}
.caret {
  width: 10px;
}
.count {
  min-width: 130px;
}
.pale-blue {
  color: #337ab7;
}
</style>
