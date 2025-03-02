<template>
  <div>
    <div v-if="isMenuOpen">
      <div class="font-size-14 font-weight-500 pt-2">
        Duplicate Course
      </div>
      <div class="my-2">
        <b-select
          id="add-course-select"
          v-model="selected"
          :disabled="isSaving || !options.length"
          :lazy="true"
          no-caret
          :toggle-text="`Assign a course to category ${parentCategory.name}`"
        >
          <b-select-option
            id="add-course-select-option-null"
            :value="null"
            @click="onSelect"
          >
            Choose...
          </b-select-option>
          <b-form-select-option
            v-for="option in options"
            :id="`add-course-select-option-${option.id}`"
            :key="option.id"
            :value="option"
            @click="onSelect"
          >
            {{ option.name }}
          </b-form-select-option>
        </b-select>
      </div>
      <div class="d-flex mt-3">
        <div>
          <b-btn
            id="add-course-save-btn"
            class="btn-primary-color-override"
            :disabled="isSaving || !selected"
            variant="primary"
            @click="onClickSave"
          >
            <span v-if="isSaving">
              <font-awesome class="mr-1" icon="spinner" spin /> Saving
            </span>
            <span v-if="!isSaving">Save</span>
          </b-btn>
        </div>
        <div>
          <b-btn
            id="add-course-cancel-btn"
            :disabled="isSaving"
            variant="link"
            @click="cancel"
          >
            Cancel
          </b-btn>
        </div>
      </div>
    </div>
    <div v-if="!isMenuOpen">
      <span v-if="!options.length" aria-live="polite" class="sr-only">No courses available to copy.</span>
      <b-btn
        v-if="$currentUser.canEditDegreeProgress"
        :id="`column-${position}-add-course-to-category-${parentCategory.id}`"
        class="align-items-center d-flex flex-row-reverse p-0"
        :disabled="disableButtons || !options.length"
        variant="link"
        @click.prevent="openMenu"
      >
        <div class="font-size-16 text-nowrap">
          Duplicate Course<span class="sr-only"> to {{ parentCategory.categoryType }} "{{ parentCategory.name }}"</span>
        </div>
        <div class="font-size-14 pr-1">
          <font-awesome icon="plus" />
        </div>
      </b-btn>
    </div>
  </div>
</template>

<script>
import DegreeEditSession from '@/mixins/DegreeEditSession'
import Util from '@/mixins/Util'

export default {
  name: 'AddCourseToCategory',
  mixins: [DegreeEditSession, Util],
  props: {
    coursesAlreadyAdded: {
      required: true,
      type: Array
    },
    parentCategory: {
      required: true,
      type: Object
    },
    position: {
      required: true,
      type: Number
    }
  },
  data: () => ({
    isMenuOpen: false,
    isSaving: false,
    selected: null
  }),
  computed: {
    options() {
      const keysAdded = this.$_.map(this.coursesAlreadyAdded, course => this.getCourseKey(course))
      return this.$_.filter(this.courses.assigned, c => !c.isCopy && !keysAdded.includes(this.getCourseKey(c)))
    }
  },
  methods: {
    cancel() {
      this.isMenuOpen = this.isSaving = false
      this.setDisableButtons(false)
      this.$announcer.polite('Canceled')
      this.$putFocusNextTick(`column-${this.position}-add-course-to-category-${this.parentCategory.id}`)
    },
    onClickSave() {
      this.isSaving = true
      this.$announcer.polite('Saving')
      // This 'Course Requirement' category will be deleted if/when the course is unassigned.
      this.copyCourse({
        categoryId: this.parentCategory.id,
        courseId: this.selected.id
      }).then(course => {
        this.isMenuOpen = this.isSaving = false
        this.selected = null
        this.setDisableButtons(false)
        this.$announcer.polite(`Course added to ${this.parentCategory.name}`)
        this.$putFocusNextTick(`assign-course-${course.id}-menu-container`, 'button')
      })
    },
    onSelect() {
      this.$announcer.polite(this.selected ? `${this.selected.name} selected` : 'Selection set to null.')
    },
    openMenu() {
      this.setDisableButtons(true)
      this.isMenuOpen = true
      this.$announcer.polite('The \'Duplicate Course\' menu is open.')
      this.$putFocusNextTick('add-course-select')
    }
  }
}
</script>
