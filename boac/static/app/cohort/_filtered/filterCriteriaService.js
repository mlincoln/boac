/**
 * Copyright ©2018. The Regents of the University of California (Regents). All Rights Reserved.
 *
 * Permission to use, copy, modify, and distribute this software and its documentation
 * for educational, research, and not-for-profit purposes, without fee and without a
 * signed licensing agreement, is hereby granted, provided that the above copyright
 * notice, this paragraph and the following two paragraphs appear in all copies,
 * modifications, and distributions.
 *
 * Contact The Office of Technology Licensing, UC Berkeley, 2150 Shattuck Avenue,
 * Suite 510, Berkeley, CA 94720-1620, (510) 643-7201, otl@berkeley.edu,
 * http://ipira.berkeley.edu/industry-info for commercial licensing opportunities.
 *
 * IN NO EVENT SHALL REGENTS BE LIABLE TO ANY PARTY FOR DIRECT, INDIRECT, SPECIAL,
 * INCIDENTAL, OR CONSEQUENTIAL DAMAGES, INCLUDING LOST PROFITS, ARISING OUT OF
 * THE USE OF THIS SOFTWARE AND ITS DOCUMENTATION, EVEN IF REGENTS HAS BEEN ADVISED
 * OF THE POSSIBILITY OF SUCH DAMAGE.
 *
 * REGENTS SPECIFICALLY DISCLAIMS ANY WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
 * IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE. THE
 * SOFTWARE AND ACCOMPANYING DOCUMENTATION, IF ANY, PROVIDED HEREUNDER IS PROVIDED
 * "AS IS". REGENTS HAS NO OBLIGATION TO PROVIDE MAINTENANCE, SUPPORT, UPDATES,
 * ENHANCEMENTS, OR MODIFICATIONS.
 */

(function(angular) {

  'use strict';

  angular.module('boac').service('filterCriteriaService', function(
    $location,
    athleticsFactory,
    authService,
    filterCriteriaFactory,
    studentFactory,
    userFactory
  ) {

    var getCohortIdFromLocation = function() {
      return parseInt($location.search().c, 10);
    };

    var getCriteriaFromLocation = function() {
      var queryArgs = _.clone($location.search());
      var criteria = {};

      _.each(filterCriteriaFactory.filterDefinitions, function(c) {
        criteria[c.filter] = c.handler(queryArgs[c.param]);
      });
      return criteria;
    };

    var updateLocation = function(filterCriteria) {
      // Clear browser location then update
      $location.url($location.path());
      var filterDefinitions = filterCriteriaFactory.filterDefinitions();

      _.each(filterCriteria, function(value, filterName) {
        var definition = _.find(filterDefinitions, ['filter', filterName]);
        if (definition && !_.isNil(value)) {
          $location.search(definition.param, value);
        }
      });
    };

    /**
     * @param  {Array}     allOptions     All options of dropdown
     * @param  {Function}  isSelected     Determines value of 'selected' property
     * @return {void}
     */
    var setSelected = function(allOptions, isSelected) {
      _.each(allOptions, function(option) {
        if (option) {
          option.selected = isSelected(option);
        }
      });
    };

    /**
     * @param  {String}    menuName      For example, 'majors'
     * @param  {Object}    optionGroup   Menu represents a group of options (see option-group definition)
     * @return {void}
     */
    var onClickMajorOptionGroup = function(menuName, optionGroup) {
      if (menuName === 'majors') {
        if (optionGroup.selected) {
          if (optionGroup.name === 'Declared') {
            // If user selects "Declared" then all other checkboxes are deselected
            $scope.search.count.majors = 1;
            setSelected($scope.search.options.majors, function(major) {
              return major.name === optionGroup.name;
            });
          } else if (optionGroup.name === 'Undeclared') {
            // If user selects "Undeclared" then "Declared" is deselected
            manualSetSelected(menuName, 'Declared', false);
            onClickOption(menuName, optionGroup);
          }
        } else {
          onClickOption(menuName, optionGroup);
        }
      }
    };

    var getMajors = function(callback) {
      studentFactory.getRelevantMajors().then(function(response) {
        // Remove '*-undeclared' options in favor of generic 'Undeclared'
        var majors = _.filter(response.data, function(major) {
          return !major.match(/undeclared/i);
        });
        majors = _.map(majors, function(name) {
          return {
            name: name,
            value: name
          };
        });
        majors.unshift(
          {
            name: 'Declared',
            value: 'Declared',
            onClick: onClickMajorOptionGroup
          },
          {
            name: 'Undeclared',
            value: 'Undeclared',
            onClick: onClickMajorOptionGroup
          },
          null
        );
        return callback(majors);
      });
    };

    var setMenuOptions = function(definitions, key, options) {
      _.find(definitions, ['key', key]).options = options;
    };

    /**
     * @param   {Object}      definitions         Filter definitions will be populated according to user privileges.
     * @param   {Function}    callback            Standard callback
     * @returns {Array}                           Available filter-criteria with populated menu options.
     */
    var loadFilterOptions = function(definitions, callback) {
      async.series([
        function(done) {
          getMajors(function(majors) {
            setMenuOptions(definitions, 'majors', majors);
            setMenuOptions(definitions, 'gpaRanges', studentFactory.getGpaRanges());
            setMenuOptions(definitions, 'levels', studentFactory.getStudentLevels());
            setMenuOptions(definitions, 'unitRanges', studentFactory.getUnitRanges());

            return done();
          });
        },
        function(done) {
          if (authService.canViewAsc()) {
            athleticsFactory.getAllTeamGroups().then(function(response) {
              setMenuOptions(definitions, 'groupCodes', _.map(response.data, function(group) {
                return {
                  name: group.name,
                  value: group.groupCode
                };
              }));
              return done();
            });
          } else {
            return done();
          }
        },
        function(done) {
          if (authService.canViewCoe()) {
            // The 'Advisor' dropdown has UIDs and names
            userFactory.getProfilesPerDeptCode('COENG').then(function(response) {
              setMenuOptions(definitions, 'advisorLdapUid', _.map(response.data, function(user) {
                return {
                  name: user.firstName + ' ' + user.lastName,
                  value: user.uid
                };
              }));
              return done();
            });
          } else {
            return done();
          }
        },
        function() {
          return callback(definitions);
        }
      ]);
    };

    return {
      getCohortIdFromLocation: getCohortIdFromLocation,
      getCriteriaFromLocation: getCriteriaFromLocation,
      getMajors: getMajors,
      loadFilterOptions: loadFilterOptions,
      updateLocation: updateLocation
    };

  });
}(window.angular));
