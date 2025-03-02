<template>
  <div class="py-2">
    <div class="d-flex flex-wrap h-100">
      <div class="gpa text-center py-2">
        <div id="cumulative-gpa" class="data-number">
          <span v-if="!$_.isNil(cumulativeGPA)">{{ round(cumulativeGPA, 3) }}</span>
          <span v-if="$_.isNil(cumulativeGPA)">--</span>
          <span v-if="$_.isNil(cumulativeGPA)" class="sr-only">No data</span>
        </div>
        <div class="gpa-label text-uppercase">Cumulative GPA</div>
      </div>
      <div id="gpa-trends" class="border-left gpa-trends py-2">
        <div id="gpa-chart" class="ml-4">
          <div class="align-items-end d-flex justify-content-between">
            <h4 class="font-weight-bold gpa-trends-label mb-1 text-uppercase">GPA Trends</h4>
            <b-btn
              v-if="!$_.isEmpty(student.termGpa)"
              id="show-hide-term-gpa-button"
              aria-controls="term-gpa-collapse"
              class="gpa-trends-more-button col-auto"
              variant="link"
              @click="showHideTermGpa"
            >
              {{ showTermGpa ? 'Less' : 'More' }}
            </b-btn>
          </div>
          <StudentGpaChart
            v-if="$_.get(student, 'termGpa.length') > 1"
            :chart-description="`Chart of GPA over time. ${student.name}'s `"
            class="gpa-trends-chart"
            :student="student"
          />
          <div v-if="$_.isEmpty(student.termGpa)" class="gpa-trends-label">
            GPA Not Yet Available
          </div>
          <div v-if="!$_.isEmpty(student.termGpa)" id="current-term-gpa" class="current-term-gpa">
            <span class="gpa-label text-uppercase">{{ student.termGpa[0].name }} GPA:</span>
            <span
              :class="{'gpa-last-term': student.termGpa[0].gpa >= 2, 'gpa-alert': student.termGpa[0].gpa < 2}"
              class="font-weight-bold"
            >
              {{ round(student.termGpa[0].gpa, 3) }}
            </span>
          </div>
        </div>
      </div>
    </div>
    <div>
      <b-collapse
        id="term-gpa-collapse"
        v-model="showTermGpa"
        class="border-top mr-3"
      >
        <div class="px-4">
          <table
            id="table-with-gpa-per-term"
            class="term-gpa-table w-100"
          >
            <tr>
              <th class="pt-0 pb-3 text-muted">Term</th>
              <th class="pt-0 pb-3 text-muted text-right">GPA</th>
            </tr>
            <tr
              v-for="(term, index) in student.termGpa"
              :key="index"
              :class="{'bg-light': index % 2 === 0}"
            >
              <td class="text-nowrap">{{ term.name }}</td>
              <td class="text-nowrap text-right">
                <font-awesome v-if="term.gpa < 2" icon="exclamation-triangle" class="text-danger pr-2" />
                <span v-if="term.gpa < 2" class="sr-only">Low GPA in {{ term.name }}: </span>
                <span
                  :id="`student-gpa-term-${term.name}`"
                  :class="{'text-danger': term.gpa < 2}"
                >{{ round(term.gpa, 3) }}</span>
              </td>
            </tr>
            <tr
              v-if="$_.isEmpty(student.termGpa)"
              id="student-gpa-no-terms"
            >
              <td>No previous terms</td>
              <td>--</td>
            </tr>
          </table>
        </div>
      </b-collapse>
    </div>
  </div>
</template>

<script>
import StudentGpaChart from '@/components/student/StudentGpaChart'
import Context from '@/mixins/Context'
import Util from '@/mixins/Util'

export default {
  name: 'StudentProfileGPA',
  components: {
    StudentGpaChart
  },
  mixins: [Context, Util],
  props: {
    student: Object
  },
  data: () => ({
    cumulativeGPA: undefined,
    showTermGpa: false
  }),
  created() {
    this.cumulativeGPA = this.$_.get(this.student, 'sisProfile.cumulativeGPA')
  },
  methods: {
    showHideTermGpa() {
      this.showTermGpa = !this.showTermGpa
      this.$announcer.polite(`The table with GPA per term is now ${this.showTermGpa ? 'visible' : 'hidden'}.`)
    }
  }
}
</script>

<style scoped>
.current-term-gpa {
  line-height: 1;
}
.data-number {
  font-size: 28px;
  line-height: 1.4em;
}
.gpa {
  font-weight: 700;
  margin-left: 20px;
  min-width: 120px;
  white-space: nowrap;
  width: 40%;
}
.gpa-alert {
  color: #d0021b;
  font-size: 11px;
}
.gpa-label {
  color: #999;
  font-size: 11px;
}
.gpa-last-term {
  color: #000;
  font-size: 11px;
  font-weight: 700;
}
.gpa-trends {
  min-width: 205px;
  width: 50%;
}
.gpa-trends-chart {
  min-width: 180px;
  width: 100%;
}
.gpa-trends-label {
  color: #555;
  font-size: 11px;
}
.gpa-trends-more-button {
  border: 0;
  font-size: 12px;
  padding: 0;
  text-align: right;
}
.show-hide-caret {
  width: 12px;
}
.term-gpa-table {
  line-height: 1.2em;
  margin: 10px 0;
}
.term-gpa-table td {
  padding: 3px 0;
}
.term-gpa-table th {
  padding: 15px 0 3px 0;
}
</style>
