<template>
  <div :id="`column-${position}-edit-category`" class="pb-3">
    <div v-if="!existingCategory">
      <div class="font-weight-500">
        Requirement Type (required)
      </div>
      <div class="pb-1">
        <b-select
          :id="`column-${position}-add-category-select`"
          v-model="selectedCategoryType"
          :disabled="isSaving"
          @change="onChangeCategorySelect"
        >
          <b-select-option :id="`column-${position}-select-option-null`" :value="null">Choose...</b-select-option>
          <b-select-option
            v-for="option in $config.degreeCategoryTypeOptions"
            :id="`column-${position}-select-option-${option}`"
            :key="option"
            :disabled="disableCategoryOption(option)"
            required
            :value="option"
          >
            {{ option }}
          </b-select-option>
        </b-select>
      </div>
    </div>
    <div v-if="selectedCategoryType" class="pb-1">
      <div v-if="!isCampusRequirements(existingCategory)">
        <div class="font-weight-500">
          {{ selectedCategoryType }} Name (required)
        </div>
        <div class="pb-1">
          <b-form-input
            :id="`column-${position}-name-input`"
            v-model="name"
            :disabled="isSaving"
            maxlength="255"
            @keypress.enter="onSubmit"
          />
          <div class="pl-1">
            <span class="faint-text font-size-12">255 character limit <span v-if="name.length">({{ 255 - name.length }} left)</span></span>
            <span v-if="name.length === 255" class="sr-only" aria-live="polite">
              Fulfillment requirement name cannot exceed 255 characters.
            </span>
          </div>
        </div>
      </div>
      <div v-if="existingCategory && isCampusRequirements(existingCategory)" class="pb-1">
        <h3 :id="`column-${position}-name`" class="font-weight-bold font-size-18">{{ name }}</h3>
      </div>
      <div v-if="selectedCategoryType === 'Course Requirement'" class="pb-1">
        <UnitsInput
          :disable="isSaving"
          :error-message="unitsErrorMessage"
          :on-submit="onSubmit"
          :range="true"
          :set-units-lower="setUnitsLower"
          :set-units-upper="setUnitsUpper"
          :units-lower="unitsLower"
          :units-upper="unitsUpper"
        />
      </div>
      <div v-if="unitRequirements.length && !isCampusRequirements(existingCategory)">
        <div class="font-weight-500 pb-1">
          Requirement Fulfillment
        </div>
        <div class="mb-3">
          <SelectUnitFulfillment
            :ref="`column-${position}-unit-requirement-select`"
            :disable="isSaving"
            :initial-unit-requirements="selectedUnitRequirements"
            :on-unit-requirements-change="onUnitRequirementsChange"
            :position="position"
          />
        </div>
      </div>
      <div v-if="selectedCategoryType !== 'Course Requirement'" class="pb-1">
        <div class="font-weight-500">
          {{ selectedCategoryType }} Description
        </div>
        <div>
          <b-form-textarea
            :id="`column-${position}-description-input`"
            v-model="descriptionText"
            :disabled="isSaving"
            rows="4"
          />
        </div>
      </div>
      <div v-if="!$_.includes(['Category', 'Campus Requirements'], selectedCategoryType)" class="pb-1">
        <div class="font-weight-500 pb-1">
          Requirement Location (required)
        </div>
        <div class="pb-1">
          <b-select
            :id="`column-${position}-parent-category-select`"
            v-model="selectedParentCategory"
            :disabled="isSaving"
            required
            @change="onChangeParentCategory"
          >
            <b-select-option
              :id="`column-${position}-parent-select-option-null`"
              :value="null"
            >
              Choose...
            </b-select-option>
            <b-select-option
              v-for="category in withTypeCategoryOrSubcategory"
              :id="`column-${position}-parent-select-option-${category.name}`"
              :key="category.id"
              :aria-label="`${category.categoryType} ${category.name}`"
              :disabled="disableLocationOption(category)"
              :value="category"
            >
              {{ category.name }}
            </b-select-option>
          </b-select>
        </div>
      </div>
    </div>
    <div class="d-flex mt-2">
      <div class="pr-2">
        <b-btn
          :id="`column-${position}-create-requirement-btn`"
          class="btn-primary-color-override"
          :disabled="disableSaveButton"
          size="sm"
          variant="primary"
          @click="onSubmit"
        >
          <span v-if="isSaving">
            <font-awesome class="mr-1" icon="spinner" spin /> Saving
          </span>
          <span v-if="existingCategory && !isSaving">Save</span>
          <span v-if="!existingCategory && !isSaving">Create Requirement</span>
        </b-btn>
      </div>
      <div>
        <b-btn
          :id="`column-${position}-cancel-create-requirement-btn`"
          class="btn-primary-color-override btn-primary-color-outline-override"
          :disabled="isSaving"
          size="sm"
          variant="outline-primary"
          @click="cancel"
        >
          Cancel
        </b-btn>
      </div>
    </div>
  </div>
</template>

<script>
import DegreeEditSession from '@/mixins/DegreeEditSession'
import SelectUnitFulfillment from '@/components/degree/SelectUnitFulfillment'
import UnitsInput from '@/components/degree/UnitsInput'
import Util from '@/mixins/Util'

export default {
  name: 'EditCategory',
  mixins: [DegreeEditSession, Util],
  components: {UnitsInput, SelectUnitFulfillment},
  props: {
    afterCancel: {
      required: true,
      type: Function
    },
    afterSave: {
      required: true,
      type: Function
    },
    existingCategory: {
      default: undefined,
      required: false,
      type: Object
    },
    position: {
      required: true,
      type: Number
    }
  },
  computed: {
    disableSaveButton() {
      return this.isSaving
        || !this.selectedCategoryType
        || (!this.isCampusRequirements(this.existingCategory) && !this.name.trim())
        || (!this.$_.includes(['Category', 'Campus Requirements'], this.selectedCategoryType) && !this.selectedParentCategory)
        || !!this.unitsErrorMessage
    },
    hasCampusRequirements() {
      return this.$_.some(this.findCategoriesByTypes(['Category']), this.isCampusRequirements)
    },
    unitsErrorMessage() {
      const validate = this.selectedCategoryType === 'Course Requirement' && (!!this.unitsLower || !!this.unitsUpper)
      return validate ? this.validateUnitRange(this.unitsLower, this.unitsUpper, 10).message : null
    },
    withTypeCategory() {
      return this.$_.reject(this.findCategoriesByTypes(['Category'], this.position), this.isCampusRequirements)
    },
    withTypeCategoryOrSubcategory() {
      return this.$_.reject(this.findCategoriesByTypes(['Category', 'Subcategory'], this.position), this.isCampusRequirements)
    }
  },
  data: () => ({
    descriptionText: undefined,
    isSaving: false,
    name: '',
    selectedCategoryType: null,
    selectedParentCategory: null,
    selectedUnitRequirements: [],
    unitsLower: undefined,
    unitsUpper: undefined
  }),
  created() {
    if (this.existingCategory) {
      this.descriptionText = this.existingCategory.description
      this.name = this.existingCategory.name
      this.selectedCategoryType = this.existingCategory.categoryType
      this.selectedParentCategory = this.findCategoryById(this.existingCategory.parentCategoryId)
      this.selectedUnitRequirements = this.$_.clone(this.existingCategory.unitRequirements)
      this.unitsLower = this.existingCategory.unitsLower
      this.unitsUpper = this.existingCategory.unitsUpper
      this.$putFocusNextTick(`column-${this.position}-name-input`)
    } else {
      this.$putFocusNextTick(`column-${this.position}-add-category-select`)
    }
  },
  methods: {
    cancel() {
      this.descriptionText = null
      this.name = ''
      this.selectedCategoryType = null
      this.afterCancel()
    },
    disableCategoryOption(option) {
      return (option === 'Campus Requirements' && this.hasCampusRequirements)
        || (!this.withTypeCategory.length && !this.$_.includes(['Category', 'Campus Requirements'], option))
    },
    disableLocationOption(option) {
      const optionType = option.categoryType
      const selectedType = this.selectedCategoryType
      return (selectedType === 'Subcategory' && optionType === 'Subcategory')
        || (selectedType === 'Subcategory' && optionType === 'Category' && this.getItemsForCoursesTable(option).length > 0)
        || (selectedType === 'Course Requirement' && optionType === 'Category' && !!option.subcategories.length)
    },
    isCampusRequirements(category) {
      return this.selectedCategoryType === 'Campus Requirements'
        || (category && !this.$_.isEmpty(category.courseRequirements) && this.$_.every(category.courseRequirements, this.isCampusRequirement))
    },
    onChangeCategorySelect(option) {
      this.$announcer.polite(option ? `${this.selectedCategoryType} selected` : 'Unselected')
      if (option) {
        if (this.selectedCategoryType === 'Campus Requirements') {
          this.name = 'Campus Requirements'
          this.descriptionText = 'American History, American Institutions, and American Cultures courses can also count as H/SS courses.'
          this.$putFocusNextTick(`column-${this.position}-description-input`)
        } else {
          this.descriptionText = null
          this.name = ''
          this.$putFocusNextTick(`column-${this.position}-name-input`)
        }
      }
    },
    onChangeParentCategory(option) {
      this.$announcer.polite(option ? `${this.selectedParentCategory.name} selected` : 'Unselected')
      const existingUnitRequirements = this.selectedUnitRequirements
      const parentUnitRequirements = this.$_.get(this.selectedParentCategory, 'unitRequirements')

      if (option) {
        const inheritedUnitRequirements = this.$_.differenceBy(parentUnitRequirements, existingUnitRequirements, 'id')
        this.$_.each(inheritedUnitRequirements, unitRequirement => {
          this.$refs[`column-${option.position}-unit-requirement-select`].onChangeUnitRequirement(unitRequirement)
        })
        this.$putFocusNextTick(`column-${this.position}-create-requirement-btn`)
      } else {
        this.$_.each(parentUnitRequirements, unitRequirement => this.removeUnitRequirement(unitRequirement))
      }
    },
    onSubmit() {
      if (!this.disableSaveButton) {
        this.isSaving = true
        const parentCategoryId = this.selectedParentCategory && this.selectedParentCategory.id
        const unitRequirementIds = this.$_.map(this.selectedUnitRequirements, 'id')
        const done = () => {
          this.$announcer.polite(`${this.selectedCategoryType} ${this.existingCategory ? 'updated' : 'created'}`)
          this.afterSave()
        }
        if (this.existingCategory) {
          this.updateCategory({
            categoryId: this.existingCategory.id,
            description: this.descriptionText,
            name: this.name,
            parentCategoryId: parentCategoryId,
            unitRequirementIds: unitRequirementIds,
            unitsLower: this.unitsLower,
            unitsUpper: this.unitsUpper
          }).then(done)
        } else {
          this.createCategory({
            categoryType: this.selectedCategoryType,
            description: this.descriptionText,
            name: this.name,
            position: this.position,
            parentCategoryId: parentCategoryId,
            unitRequirementIds: unitRequirementIds,
            unitsLower: this.unitsLower,
            unitsUpper: this.unitsUpper
          }).then(done)
        }
      }
    },
    onUnitRequirementsChange(unitRequirements) {
      this.selectedUnitRequirements = unitRequirements
    },
    setUnitsLower(units) {
      this.unitsLower = units
    },
    setUnitsUpper(units) {
      this.unitsUpper = units
    }
  }
}
</script>
