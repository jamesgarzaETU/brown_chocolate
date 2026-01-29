/*
function createFilterData(
  data,
  filter_vars
){

  var domainValues = [];
  filter_vars.forEach(function(vFilter, iFilter){

    domainValues[iFilter] = [];

    Array.from(new Set(data.map(d => d[vFilter]))).forEach(function(v, i){

      domainValues[iFilter].push({
        'include': true,
        'bucket_orig': i,
        'bucket': i,
        'value': v,
      })
    });
  });

  return domainValues;
}
*/



function createFilterData(data){

  var domainValues = [];
  Array.from(new Set(data.map(d => d["demog_var"]))).forEach(function(vDemogVar, iDemogVar){

    domainValues[iDemogVar] = [];

    data.filter(d =>  d["demog_var"] == vDemogVar).map(d => d["demog_val"]).forEach(function(vDemogVal, iDemogVal){

      domainValues[iDemogVar].push({
        'include': true,
        'bucket_orig': iDemogVal,
        'bucket': iDemogVal,
        'value': vDemogVal,
      })
    });
  });

  return domainValues;
}
