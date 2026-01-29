// ----- Function to perform the equivalent of GROUP_CONCAT ----->
function groupConcat(data, groupBy, concatColumn, separator) {
  const groupedData = {};

  // Iterate over each row in the data
  data.forEach(row => {
    // Extract the key for grouping
    const key = row[groupBy];

    // If the key doesn't exist in groupedData, initialize it with an empty array
    if (!groupedData[key]) {
      groupedData[key] = [];
    }

    // Push the value of the column to the array for the corresponding key
    groupedData[key].push(row[concatColumn]);
  });

  // Convert the groupedData object to the desired format
  const result = Object.entries(groupedData).map(([key, values]) => ({
    [groupBy]: key,
    [concatColumn]: values.join(separator)
  }));

  return result;
}





// ----- Function to group and sum the data ----->
function groupAndSum(data, groupBy, sumVars) {
  const groupedData = {};

  // Iterate over each row in the data
  data.forEach(row => {
    // Generate a unique key based on groupBy variables
    const key = groupBy.map(variable => row[variable]).join('-');

    // If the key doesn't exist in groupedData, initialize it with sumVars as 0
    if (!groupedData[key]) {
      groupedData[key] = Object.assign({}, ...groupBy.map(variable => ({ [variable]: row[variable] })), ...sumVars.map(variable => ({ [variable]: 0 })));
    }

    // Increment the sum by n for the corresponding key
    sumVars.forEach(variable => {
      groupedData[key][variable] += row[variable];
    });
  });

  // Convert the object back to an array
  const result = Object.values(groupedData);

  return result;
}





function createSummaryData(){

  //dataSummary = [];
  Object.keys(data_component_dmg).forEach(function(vSemi, iSemi){
    //dataSummary[iSemi] = [];
    data_component_dmg[vSemi]['dataSummary'] = [];

    // Filter data based on "included" values in all filters
    var dataSlice = data_component_dmg[vSemi]['dataSemi'].filter(d => true);
    dataFilter.forEach(function(vFilter, iFilter){
      dataSlice = dataSlice.filter(d => Array.from(new Set(vFilter.filter(d => d['include'] == true).map(d => d['value']))).includes(d[filters[iFilter]]));
    });
    //console.log('dataSlice:', dataSlice);

    if(dataSlice.length > 0){

      dataSlice_vars = Object.keys(dataSlice[0]);

      var keep_vars = [];
      var stat_vars = [];
      dataSlice_vars.forEach(function(vVar, iVar){
        if (vVar.indexOf("_") == 0){ stat_vars.push(vVar) }
        //else if (vVar == selected_filter){ keep_vars.push(vVar) }
        else if (!filters.includes(vVar) && vVar != selected_filter){ keep_vars.push(vVar) }
      });
      //console.log('keep_vars:', keep_vars, 'stat_vars:', stat_vars);



      var grouped_filter = groupConcat(dataFilter[filters.indexOf(selected_filter)].filter(d => d['include'] == true), 'bucket', 'value', '<br>+ ');
      //console.log('grouped_filter:', grouped_filter);
      grouped_filter.forEach(function(vGroupedFilter, iGroupedFilter){
        var split_filter_vals = vGroupedFilter['value'].split("<br>+ ");

        var dataSlice_Filter = dataSlice.filter(d => split_filter_vals.includes(d[selected_filter]));
        var dataSlice_Filter_Grouped = groupAndSum(dataSlice_Filter, keep_vars, stat_vars);
        dataSlice_Filter_Grouped.forEach(function(vRow, iRow){
          vRow[selected_filter] = vGroupedFilter['value'];
          if(stat_vars.includes("_tot") && stat_vars.includes("_n")){
            vRow['_avg'] = vRow['_tot']/vRow['_n'];
          }
          //dataSummary[iSemi].push(vRow)
          data_component_dmg[vSemi]['dataSummary'].push(vRow)
        })
        //console.log('dataSlice_Filter_Grouped:', dataSlice_Filter_Grouped);
      });
    }

    //console.log(iSemi, 'dataSummary:', data_component_dmg[iSemi]['dataSummary'])

  });

  //console.log('dataSummary:', dataSummary)

  //console.log('data_component_dmg:', data_component_dmg)
  //return dataSummary;

  updateGraphs_dmg();
}
