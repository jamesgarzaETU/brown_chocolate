function chart_donut(
  data,
  html_id,

  title={value:[{size:40, weight:700, text:null}, {size:32, weight:700, text:null}], line:false},

  clr={
    var:'clr',
    palette:null, // 'plotly', 'd3', 'g10', 't10', 'alphabet', 'dark24', 'light24', 'set1', 'pastel1'
    value:'#e32726'
  }, // Variable containing color of bar(s), a name of a pre-defined palette of colors, or value to set all bars to same color

  facet={var:null, size:18, weight:400, space_above_title:5, order:'as_appear', ascending:true, line:{show:false, color:'#d3d2d2'}},
  group={var:null, label:{value:null, size:18, weight:700}, size:18, weight:400, order:'as_appear', ascending:true, show:true},
  switcher={var:null, label:{value:null, size:18, weight:700}, size:18, weight:400, order:'as_appear', ascending:true, line:false},
  scroll={var:null, label:{value:null, size:20, weight:700}, size:18, weight:400, order:'as_appear', ascending:true, line:false},

  value={
    var:null, // name of the variable that contains the values for the circle bars
    max:null,
    maxScroll:'fixed', // 'fixed' or 'free'
    maxFacet:'fixed', // 'fixed' or 'free'
  },

  segment_label={
    minValue:0.05, // value between 0 and 1 representing the minimum percentage of the circle that a segment must reach before a segment label is shown
    text:[
      {size:20, weight:700, text:[{var:'stat', format:null, prefix:null, suffix:' Attempt(s)'}]},
      {size:20, weight:400, text:[{var:'pct', format:',.1f', prefix:null, suffix:'%'}]},
      {size:14, weight:400, text:[
        {var:'n', format:',.0f', prefix:null, suffix:null},
        {var:'tot', format:',.0f', prefix:'/', suffix:null}
      ]}
    ]
  },

  tooltip_text=[
    {size:16, weight:700, text:[{var:'stat', format:null, prefix:null, suffix:' Attempt(s)'}]},
    {size:16, weight:400, text:[{var:'pct', format:'.1f', prefix:null, suffix:'%'}]},
    {size:14, weight:400, text:[
      {var:'n', format:',.0f', prefix:null, suffix:null},
      {var:'tot', format:',.0f', prefix:'/', suffix:null}
    ]}
  ],

  inner_circle={
    clr:'#d3d2d2',
    width:0.5, // Value between 0 and 1 representing the percentage width of the outer circle
    show:true
  },

  inner_radius=0.6, // Value between 0 and 1. The higher the value, the thinner the donut

  inner_text=[
    {size:20, weight:700, text:[
      {var:'pct', aggregate:'sum', format:',.1f', prefix:null, suffix:'%'},
    ]},
    {size:18, weight:400, text:[
      {var:'value', aggregate:'sum', format:',.0f', prefix:null, suffix:null},
      {var:'total', aggregate:'max', format:',.0f', prefix:' / ', suffix:null},
    ]},
  ],

  yaxis={
    height:300,
    offset:{top:10, bottom:10},
    tick:{width:250}
  },

  font={family:'Catamaran'},

  margin={top:10, bottom:10, left:10, right:10, g:10},

  canvas={width:960},

  zoom=true
){


  // -------------------------->
  // ----- Color Palettes ----->
  // -------------------------->

  var palette = {
    'plotly': ['#636EFA', '#EF553B', '#00CC96', '#AB63FA', '#FFA15A', '#19D3F3', '#FF6692', '#B6E880', '#FF97FF', '#FECB52'],
    'd3': ['#1F77B4', '#FF7F0E', '#2CA02C', '#D62728', '#9467BD', '#8C564B', '#E377C2', '#7F7F7F', '#BCBD22', '#17BECF'],
    'g10': ['#3366CC', '#DC3912', '#FF9900', '#109618', '#990099', '#0099C6', '#DD4477', '#66AA00', '#B82E2E', '#316395'],
    't10': ['#4C78A8', '#F58518', '#E45756', '#72B7B2', '#54A24B', '#EECA3B', '#B279A2', '#FF9DA6', '#9D755D', '#BAB0AC'],
    'alphabet': ['#AA0DFE', '#3283FE', '#85660D', '#782AB6', '#565656', '#1C8356', '#16FF32', '#F7E1A0', '#E2E2E2', '#1CBE4F', '#C4451C', '#DEA0FD', '#FE00FA', '#325A9B', '#FEAF16', '#F8A19F', '#90AD1C', '#F6222E', '#1CFFCE', '#2ED9FF', '#B10DA1', '#C075A6', '#FC1CBF', '#B00068', '#FBE426', '#FA0087'],
    'dark24': ['#2E91E5', '#E15F99', '#1CA71C', '#FB0D0D', '#DA16FF', '#222A2A', '#B68100', '#750D86', '#EB663B', '#511CFB', '#00A08B', '#FB00D1', '#FC0080', '#B2828D', '#6C7C32', '#778AAE', '#862A16', '#A777F1', '#620042', '#1616A7', '#DA60CA', '#6C4516', '#0D2A63', '#AF0038'],
    'light24': ['#FD3216', '#00FE35', '#6A76FC', '#FED4C4', '#FE00CE', '#0DF9FF', '#F6F926', '#FF9616', '#479B55', '#EEA6FB', '#DC587D', '#D626FF', '#6E899C', '#00B5F7', '#B68E00', '#C9FBE5', '#FF0092', '#22FFA7', '#E3EE9E', '#86CE00', '#BC7196', '#7E7DCD', '#FC6955', '#E48F72'],
    'set1': ['rgb(228,26,28)', 'rgb(55,126,184)', 'rgb(77,175,74)', 'rgb(152,78,163)', 'rgb(255,127,0)', 'rgb(255,255,51)', 'rgb(166,86,40)', 'rgb(247,129,191)', 'rgb(153,153,153)'],
    'pastel1': ['rgb(251,180,174)', 'rgb(179,205,227)', 'rgb(204,235,197)', 'rgb(222,203,228)', 'rgb(254,217,166)', 'rgb(255,255,204)', 'rgb(229,216,189)', 'rgb(253,218,236)', 'rgb(242,242,242)'],
  }

  var palette_names = [];
  for (const [key, value] of Object.entries(palette)) {
    palette_names.push(key);
  }

  // <--------------------------
  // <----- Color Palettes -----
  // <--------------------------





  // ----------------------------------------------->
  // ----- Function to calculate width of text ----->
  // ----------------------------------------------->

  function textWidth(text, fontSize=16, fontWeight=400, fontFamily=font.family) {

      // --- METHOD 1 --->
      /*container.append('text')
        .attr('x', -99999)
        .attr('y', -99999)
        .style('font-family', fontFamily)
        .style('font-size', fontSize + 'px')
        .style('font-weight', fontWeight)
        .text(text);

      var text_width = container.node().getBBox().width;
      container.remove();

      console.log(text, '# WIDTH 1:', text_width, '# WIDTH 2:', context.measureText(text).width)

      return { text_width };*/



      // --- METHOD 2 --->
      var context = document.createElement('canvas').getContext('2d');
      context.font = fontWeight + ' ' + fontSize + 'px ' + fontFamily;

      return context.measureText(text).width;
  }

  // <-----------------------------------------------
  // <----- Function to calculate width of text -----
  // <-----------------------------------------------




  // ------------------------------------------------------------------->
  // ----- Function to return all indices of substring in a string ----->
  // ------------------------------------------------------------------->

  function getIndicesOf(searchStr, str, caseSensitive) {
      var searchStrLen = searchStr.length;
      if (searchStrLen == 0) {
          return [];
      }
      var startIndex = 0, index, indices = [];
      if (!caseSensitive) {
          str = str.toLowerCase();
          searchStr = searchStr.toLowerCase();
      }
      while ((index = str.indexOf(searchStr, startIndex)) > -1) {
          indices.push(index);
          startIndex = index + searchStrLen;
      }
      return indices;
  }

  // <-------------------------------------------------------------------
  // <----- Function to return all indices of substring in a string -----
  // <-------------------------------------------------------------------






  // ------------------------------------------------------------->
  // ----- Function to split text to fit into assigned width ----->
  // ------------------------------------------------------------->

  function splitWrapText(text, width=100, fontSize=14, fontWeight=400, fontFamily=font.family) {

      var textSplitWrapped = [];

      var textSplit = text.split(/\n|<br>/);

      textSplit.forEach(function(v){

          var spaces = getIndicesOf(' ', v);

          for(let numSplits = 0; numSplits <= spaces.length; numSplits++){
            // No split
            if(numSplits == 0){
              if(textWidth(v, fontSize=fontSize, fontWeight=fontWeight, fontFamily=fontFamily) <= width){
                textSplitWrapped.push(v);
                break;
               }
            }
            // At least one split
            else{
               var idealSplitPoints = [], actualSplitPoints = [], actualSplit = [];
               for(let split = 1; split <= numSplits; split++){
                 idealSplitPoints.push( parseInt((v.length/(numSplits+1))*split)-1 );
               }

               var usedSpaceIndex = 0;
               idealSplitPoints.forEach(function(vIdeal, iIdeal){
                 var idealVsSpace = [];
                 spaces.forEach(function(vSpace, iSpace){
                   if(vSpace > usedSpaceIndex){
                     idealVsSpace.push({
                       'ideal': vIdeal,
                       'space': vSpace,
                       'diffAbs': Math.abs(vSpace - vIdeal),
                       'diffAct': vSpace - vIdeal
                     });
                   }
                 })

                 if(idealVsSpace.length > 0){
                   var idealVsSpace = idealVsSpace.sort((a, b) => d3.ascending(a['diffAbs'], b['diffAbs']) || d3.ascending(a['diffAct'], b['diffAct']))

                   actualSplit.push( idealVsSpace[0]['space'] )
                   usedSpaceIndex = idealVsSpace[0]['space'];
                 }

               })
               actualSplit.push( v.length )


               var vSplit = [];
               var sliceStart = 0;
               actualSplit.forEach(function(vActualSplit){
                 vSplit.push(v.slice(sliceStart, vActualSplit))

                 sliceStart = vActualSplit+1;
               })

               var vSplitMaxWidth = 0;
               vSplit.forEach(function(v_vSplit){
                 if(textWidth(v_vSplit, fontSize=fontSize, fontWeight=fontWeight, fontFamily=fontFamily) > vSplitMaxWidth){ vSplitMaxWidth = textWidth(v_vSplit, fontSize=fontSize, fontWeight=fontWeight, fontFamily=fontFamily); }
               })

               if(vSplitMaxWidth <= width){
                 vSplit.forEach(function(v_vSplit){
                   textSplitWrapped.push(v_vSplit)
                 })
                 break;
               }

               if(numSplits >= spaces.length ){
                 vSplit.forEach(function(v_vSplit){
                   textSplitWrapped.push(v_vSplit)
                 })
               }

             }

          }

          if(textSplitWrapped.length == 0){
            textSplitWrapped.push(v);
          }

      })

      return textSplitWrapped;
  }

  // <-------------------------------------------------------------
  // <----- Function to split text to fit into assigned width -----
  // <-------------------------------------------------------------





  // ------------------------------------------------------------------------------>
  // ----- Function to split list of text elements to fit into assigned width ----->
  // ------------------------------------------------------------------------------>

  function splitWrapTextElement(list, width=100, padding=10, extra_width=0, fSize=14, fWeight=400, fFamily=font.family) {

      var listSplitWrapped = [];

      // Calculate total width of all elements in one row
      var totalWidthAllItems = 0;
      var spaces = [];
      var maxLinesInPrevRow = 0;
      var maxLinesInThisRow = 0;

      list.forEach(function(text, iList){

        if(iList > 0){
          spaces.push(totalWidthAllItems)
        }

        var textSplit = text.split(/\n|<br>/);

        var maxTextWidth = 0;
        maxLinesInThisRow = 0;
        var listSplitWrappedText = [];
        textSplit.forEach(function(vTextSplit, iTextSplit){

          var thisWidth = textWidth(vTextSplit, fSize, fWeight, fFamily) + (padding*2) + extra_width;
          maxTextWidth = (thisWidth > maxTextWidth)? thisWidth: maxTextWidth;

          maxLinesInThisRow = (iTextSplit > maxLinesInThisRow)? iTextSplit: maxLinesInThisRow;

          listSplitWrappedText.push({
            'value': vTextSplit,
            'dy': Math.min(1.1, (iTextSplit*1.1)) + 'em',
            'this-width-value': thisWidth,
            'max-width-value': maxTextWidth
          })
        })

        listSplitWrapped.push({
          'line': 0,
          'text': listSplitWrappedText,
          'x': totalWidthAllItems + padding,
          'y': 0*(maxLinesInPrevRow*(fSize*1.1)),
          //'y': ((maxLinesInPrevRow*(fSize*1.1)) + 10),
          'width-value': maxTextWidth
        })

        totalWidthAllItems += maxTextWidth;
      });
      maxLinesInPrevRow = maxLinesInThisRow;



      if(totalWidthAllItems < width){
        listSplitWrapped.forEach(function(v, i){
          v['x'] = v['x'] - (totalWidthAllItems/2)
        })
        return listSplitWrapped;
      }



      for(let numSplits = 1; numSplits <= (list.length-1); numSplits++){

          var listSplitWrapped = [];

          // ----- STEP 1: Split list into numSplits amount of smaller lists ----->

          var idealSplitPoints = [], actualSplitPoints = [], actualSplit = [];
          for(let split = 1; split <= numSplits; split++){
            idealSplitPoints.push( parseInt((totalWidthAllItems/(numSplits+1))*split) );
          }


          var usedSpaceIndex = 0;
          idealSplitPoints.forEach(function(vIdeal, iIdeal){
            var idealVsSpace = [];
            spaces.forEach(function(vSpace, iSpace){
              if(vSpace > usedSpaceIndex){
                idealVsSpace.push({
                  'index': iSpace+1,
                  'ideal': vIdeal,
                  'space': vSpace,
                  'diffAbs': Math.abs(vSpace - vIdeal),
                  'diffAct': vSpace - vIdeal
                });
              }
            })

            if(idealVsSpace.length > 0){
              var idealVsSpace = idealVsSpace.sort((a, b) => d3.ascending(a['diffAbs'], b['diffAbs']) || d3.ascending(a['diffAct'], b['diffAct']))

              actualSplit.push( idealVsSpace[0]['index'] )
              usedSpaceIndex = idealVsSpace[0]['index'];
            }

          })
          actualSplit.push( list.length )

          // Split list into numSplits amount of smaller lists
          var listSplit = [];
          var indexStart = 0;
          actualSplit.forEach(function(vActualSplit, iActualSplit){
            listSplit[iActualSplit] = list.slice(indexStart, vActualSplit)
            indexStart = vActualSplit;
          })

          // <----- STEP 1: Split list into numSplits amount of smaller lists -----


          var listSplitMaxWidth = 0;
          var maxLinesInPrevRow = 0;
          var prevY = 0;
          listSplit.forEach(function(v_listSplit, i_listSplit){

              var totalWidthThisLine = 0;
              var maxLinesInRow = 0;
              var maxLinesInThisRow = 0;

              v_listSplit.forEach(function(text, i){

                var textSplit = text.split(/\n|<br>/);

                maxLinesInThisRow = (textSplit.length > maxLinesInThisRow)? textSplit.length: maxLinesInThisRow;

                var maxTextWidth = 0;
                var listSplitWrappedText = [];
                textSplit.forEach(function(vTextSplit, iTextSplit, aTextSplit){

                  maxLinesInRow = (aTextSplit.length > maxLinesInRow)? aTextSplit.length: maxLinesInRow;

                  var thisWidth = (textWidth(vTextSplit, fSize, fWeight, fFamily) + (padding*2) + extra_width);

                  maxTextWidth = (thisWidth > maxTextWidth)? thisWidth: maxTextWidth;

                  listSplitWrappedText.push({
                    'value': vTextSplit,
                    'dy': (iTextSplit*1.1) + 'em',
                    'this-width-value': thisWidth,
                    //'max-width-value': maxTextWidth
                  })
                })

                listSplitWrappedText.forEach(function(v_listSplitWrappedText){
                  v_listSplitWrappedText['max-width-value'] = maxTextWidth
                })

                listSplitWrapped.push({
                  'line': i_listSplit,
                  'text': listSplitWrappedText,
                  'x': totalWidthThisLine + padding,
                  'width-value': maxTextWidth
                })

                totalWidthThisLine += maxTextWidth;

              });

              listSplitWrapped.forEach(function(v, i3){
                if(v['line'] == i_listSplit){
                  v['x'] = v['x'] - (totalWidthThisLine/2)
                  v['y'] = prevY + (maxLinesInPrevRow*(fSize*1.1)) + ((i_listSplit > 0)? (fSize*1.1): 0)
                }
              })

              prevY += (maxLinesInPrevRow*(fSize*1.1)) + ((i_listSplit > 0)? (fSize*1.1): 0)

              maxLinesInPrevRow = maxLinesInThisRow;

              listSplitMaxWidth = (totalWidthThisLine > listSplitMaxWidth)? totalWidthThisLine: listSplitMaxWidth;
          })

          if(listSplitMaxWidth < width){ return listSplitWrapped; }
      }

      return listSplitWrapped;
  }

  // <------------------------------------------------------------------------------
  // <----- Function to split list of text elements to fit into assigned width -----
  // <------------------------------------------------------------------------------





  // ------------------------------------>
  // ----- Function to Scroll chart ----->
  // ------------------------------------>

  function scrollChart(method='up'){

    if(method == 'up'){
      var nextScrollIndex = ((scrollIndex+1) <= (domainScroll.length-1))? scrollIndex+1: 0;
    }
    else{
      var nextScrollIndex = ((scrollIndex-1) >= 0)? scrollIndex-1: (domainScroll.length-1);
    }



    // --- Move Scroll Texts --->
    svg.selectAll('.scroll_text_' + nextScrollIndex)
      .transition()
      .duration(0)
          .attr('transform', function(){
            if(method == 'up'){
              return `translate(${(canvas.width*1.5)}, ${height.scrollLabel})`
            }
            else{
              return `translate(${(-canvas.width*1.5)}, ${height.scrollLabel})`
            }
          })
      .transition()
          .duration(500)
          .attr('opacity', 1)
          .attr('transform', function(){
              return `translate(${0}, ${height.scrollLabel})`
          })


    svg.selectAll('.scroll_text_' + scrollIndex)
      .transition()
      .duration(500)
          .attr('opacity', 0)
          .attr('transform', function(d, i){
            if(method == 'up'){
              return `translate(${(-canvas.width*1.5)}, ${height.scrollLabel})`
            }
            else{
              return `translate(${(canvas.width*1.5)}, ${height.scrollLabel})`
            }
          })




    // --- Move individual charts --->
    svg.select('.g_scroll_' + nextScrollIndex)
      .transition()
      .duration(0)
          .attr('x', function(){
            (method == 'up')? canvas.width: -canvas.width
          })
          .attr('transform', function(){
            if(method == 'up'){
              return `translate(${((canvas.width*1) + margin.left)}, ${margin.top + height.title + height.scroll + height.switcher + height.legend})`
            }
            else{
              return `translate(${((-canvas.width*1) + margin.left)}, ${margin.top + height.title + height.scroll + height.switcher + height.legend})`
            }
          })
      .transition()
          .duration(500)
          .attr('opacity', 1)
          .attr('x', canvas.width*0)
          .attr('transform', function(){
              return `translate(${(margin.left)}, ${margin.top + height.title + height.scroll + height.switcher + height.legend})`
          })


    svg.select('.g_scroll_' + scrollIndex)
      .transition()
      .duration(500)
          .attr('opacity', 0)
          .attr('x', function(){
            (method == 'up')? -canvas.width: canvas.width
          })
          .attr('transform', function(d, i){
            if(method == 'up'){
              return `translate(${(-canvas.width + margin.left)}, ${margin.top + height.title + height.scroll + height.switcher + height.legend})`
            }
            else{
              return `translate(${(canvas.width + margin.left)}, ${margin.top + height.title + height.scroll + height.switcher + height.legend})`
            }
          })


    if(method == 'up'){
      scrollIndex = ((scrollIndex+1) <= (domainScroll.length-1))? scrollIndex+1: 0;
    }
    else{
      scrollIndex = ((scrollIndex-1) >= 0)? scrollIndex-1: (domainScroll.length-1);
    }

  }

  // <------------------------------------
  // <----- Function to Scroll chart -----
  // <------------------------------------










  // ------------------------>
  // ----- DATA DOMAINS ----->
  // ------------------------>


  // --- Scroll domain --->
  var domainScroll = (scroll.var != null)? Array.from(new Set(data.map(d => d[scroll.var]))): [null];
  if(scroll.var != null && scroll.order == 'alphabetical'){ domainScroll.sort(); }
  //console.log('### domainScroll', domainScroll);





  // --- Facet domain --->
  var domainFacet = []
  domainScroll.forEach(function(vScroll, iScroll){
    domainFacet[iScroll] = []

    if(facet.var != null){
      Array.from(new Set(data.filter(d => (scroll.var != null)? (d[scroll.var] == vScroll): true).map(d => d[facet.var].toString()))).forEach(function(vFacet, iFacet){

        if(value.max != null){
          var facetMaxValue = value.max;
        }
        else{

          if(value.maxFacet == 'free'){
            if(value.maxScroll == 'free'){
              var facetMaxValue = d3.sum( data.filter(d => ((scroll.var != null)? (d[scroll.var] == vScroll): true) && d[facet.var] == vFacet).map(d => d[value.var]) )
              //Math.max(data.filter(d => ((scroll.var != null)? (d[scroll.var] == vScroll): true) && d[facet.var] == vFacet).map(d => d[value.var]));
            }
            else{
              var facetMaxValue = d3.sum( data.filter(d => d[facet.var] == vFacet).map(d => d[value.var]) )
              //Math.max(data.filter(d => d[facet.var] == vFacet).map(d => d[value.var]));
            }
          }
          else{
            if(value.maxScroll == 'free'){
              var facetMaxValue = d3.sum( data.filter(d => ((scroll.var != null)? (d[scroll.var] == vScroll): true)).map(d => d[value.var]) )
              //Math.max(data.filter(d => ((scroll.var != null)? (d[scroll.var] == vScroll): true)).map(d => d[value.var]));
            }
            else{
              var facetMaxValue = d3.sum( data.map(d => d[value.var]) )
              //Math.max(data.map(d => d[value.var]));
            }
          }
        }

        domainFacet[iScroll][iFacet] = {'facet': vFacet, 'maxValue': facetMaxValue}
      })
    }
    else{

      if(value.max != null){
        var facetMaxValue = value.max;
      }
      else{

        if(value.maxScroll == 'free'){
          var facetMaxValue = d3.sum( data.filter(d => ((scroll.var != null)? (d[scroll.var] == vScroll): true)).map(d => d[value.var]) )
          //Math.max(data.filter(d => ((scroll.var != null)? (d[scroll.var] == vScroll): true)).map(d => d[value.var]));
        }
        else{
          var facetMaxValue = d3.sum( data.map(d => d[value.var]) )
          //Math.max(data.map(d => d[value.var]));
        }
      }

      domainFacet[iScroll][0] = {'facet': null, 'maxValue': facetMaxValue}
    }


    if(facet.order == 'alphabetical'){ domainFacet[iScroll].sort((a, b) => d3.ascending(a['facet'], b['facet'])); }
    if(!facet.ascending){ domainFacet[iScroll].reverse(); }

  })
  //console.log('domainFacet', domainFacet);





  // --- Group domain --->
  var domainGroup = [];
  if(group.var != null){
    Array.from(new Set(data.map(d => d[group.var]))).forEach(function(v, i){
      domainGroup.push({
        'group': v,
        'sortVar': (group.order != null && group.order != 'as_appear' && group.order != 'alphabetical')? data.filter(d => d[group.var] == v).map(d => d[group.order])[0]: null
      })
    })

  }
  else{
    domainGroup = [{
      'group':null,
      //'color':null
    }];
  }

  if(group.var != null && group.order == 'alphabetical'){
    domainGroup = domainGroup.sort((a, b) => d3.ascending(a['group'], b['group']));
  }
  if(group.var != null && group.order != null && group.order != 'as_appear' && group.order != 'alphabetical'){
    domainGroup = domainGroup.sort((a, b) => d3.ascending(a['sortVar'], b['sortVar']));
  }
  if(!group.ascending){ domainGroup.reverse(); }


  // Get colors for each group
  domainGroup.forEach(function(v, i){
    if(clr.var != null){
      v['color'] = data.filter(d => d[group.var] == v['group']).map(d => d[clr.var])[0];
    }
    else if(clr.palette != null && palette_names.includes(clr.palette.toLowerCase())){
      v['color'] = palette[clr.palette][i];
    }
    else if(clr.value != null){
      v['color'] = clr.value;
    }
    else{
        v['color'] = '#e32726';
    }
  })
  //console.log('### domainGroup', domainGroup);





  // --- Switcher domain --->
  var domainSwitcher = (switcher.var != null)? Array.from(new Set(data.map(d => d[switcher.var]))): [null];
  if(switcher.var != null && switcher.order == 'alphabetical'){ domainSwitcher.sort(); }
  //console.log('### domainSwitcher', domainSwitcher);

  // <------------------------
  // <----- DATA DOMAINS -----
  // <------------------------










  // ------------------------>
  // ----- GRAPH SIZING ----->
  // ------------------------>

  //var canvas.width = 960;
  if (canvas == undefined){
    var canvas = {width:960}
  }
  if(canvas.width == null){
    canvas.width = 960
  }

  var height = {};


  // Title Height
  height.title = 0;
  var title_ypos = [];
  if(title.value != null){
    var totTitleHeight = 0
    title.value.forEach(function(vTitle, iTitle){
      title_ypos[iTitle] = height.title;

      height.title += (vTitle.size*1.1)*splitWrapText(vTitle.text, (canvas.width - margin.left - margin.right), fontSize=vTitle.size, fontWeight=vTitle.weight, fontFamily=font.family).length;
    })

    height.title += margin.g;
  }
  //console.log('title_ypos', title_ypos)
  //console.log('height.title', height.title)



  // Scroll Height
  height.scroll = 0;
  height.scrollLabel = 0;
  if(scroll.var != null ){

    domainScroll.forEach(function(vScroll, iScroll){
      var numScrollLines = splitWrapText(vScroll, (canvas.width - margin.left - margin.right - (scroll.size*2)), fontSize=scroll.size, fontWeight=scroll.weight, fontFamily=font.family).length;

      height.scroll = (((scroll.size*1.1)*numScrollLines) > height.scroll)? ((scroll.size*1.1)*numScrollLines): height.scroll;
    })

    if(scroll.label.value != null){
      var numScrollLabelLines = splitWrapText(scroll.label.value, (canvas.width - margin.left - margin.right), fontSize=scroll.label.size, fontWeight=scroll.label.weight, fontFamily=font.family).length;
      height.scrollLabel = numScrollLabelLines*(scroll.label.size*1.1) + 5
      height.scroll += height.scrollLabel
    }

    height.scroll += margin.g;
  }




  // Switcher Height
  height.switcher = 0;
  height.switcherLabel = 0;
  if(switcher.var != null ){
    var switcherText = splitWrapTextElement(domainSwitcher, width=canvas.width-(margin.left+margin.right), padding=16, extra_width=0, fSize=switcher.size, fWeight=switcher.weight, fFamily=font.family);

    var maxY = d3.max(switcherText.map(d => d['y']));
    var maxLine = d3.max(switcherText.map(d => d['line']));
    var maxRowInLastLine = 0;

    switcherText.filter(d => d['line'] == maxLine).map(d => d['text']).forEach(function(v, i){
      if(v.length > maxRowInLastLine){ maxRowInLastLine = v.length}
    });

    if(switcher.label.value != null){
      var numSwitchLabelLines = splitWrapText(switcher.label.value, (canvas.width - margin.left - margin.right), fontSize=switcher.label.size, fontWeight=switcher.label.weight, fontFamily=font.family).length;
      height.switcherLabel = numSwitchLabelLines*(switcher.label.size*1.1) + 5
      //height.switcher += height.switcherLabel
    }

    height.switcher = margin.g + maxY + (maxRowInLastLine*(switcher.size*1.1)) + 10 + height.switcherLabel
  }



  // Legend Height
  height.legend = 0;
  height.legendLabel = 0;
  if(group.var != null ){
    if(group.show == undefined || group.show){
      var legendText = splitWrapTextElement(domainGroup.map(d => d['group']), width=canvas.width-(margin.left+margin.right), padding=10, extra_width=14+5, fSize=group.size, fWeight=group.weight, fFamily=font.family);

      // Get colors
      legendText.forEach(function(v, i){
        v['color'] = domainGroup[i]['color']
      });

      if(group.label.value != null){
        var numLegendLabelLines = splitWrapText(group.label.value, (canvas.width - margin.left - margin.right), fontSize=group.label.size, fontWeight=group.label.weight, fontFamily=font.family).length;
        height.legendLabel = numLegendLabelLines*(group.label.size*1.1) + 5
        //height.legend += height.legendLabel
      }


      var maxY = d3.max(legendText.map(d => d['y']));
      var maxLine = d3.max(legendText.map(d => d['line']));
      var maxRowInLastLine = 0;

      legendText.filter(d => d['line'] == maxLine).map(d => d['text']).forEach(function(v, i){
        if(v.length > maxRowInLastLine){ maxRowInLastLine = v.length}
      });

      height.legend = maxY + (maxRowInLastLine*(group.size*1.1)) + height.legendLabel + 10
    }
  }




  // Facet Height
  var facet_ypos = [];
  height.facetLabel = [];
  height.facet = [];

  domainFacet.forEach(function(vScroll, iScroll){

    var numFacets = 0;
    vScroll.forEach(function(vFacet, iFacet){
      numFacets += 1;
    })

    facet_ypos[iScroll] = [];
    height.facetLabel[iScroll] = [];
    height.facet[iScroll] = 0;

    var facetPos = 0;

    vScroll.forEach(function(vFacet, iFacet){
      var numFacetLabelLines = (vFacet['facet'] != null)? splitWrapText(vFacet['facet'], (canvas.width - margin.left - margin.right), fontSize=facet.size, fontWeight=facet.weight, fontFamily=font.family).length: 0;
      height.facetLabel[iScroll][iFacet] = (numFacetLabelLines*(facet.size*1.1)) + ((facet.var != null)? facet.space_above_title: 0);

      facet_ypos[iScroll][iFacet] = facetPos + height.facetLabel[iScroll][iFacet];

      facetPos += height.facetLabel[iScroll][iFacet] + yaxis.offset.top + yaxis.height + yaxis.offset.bottom;
    })

    height.facet[iScroll] += d3.sum(height.facetLabel[iScroll]);
  })
  //console.log('height.facetLabel', height.facetLabel)
  //console.log('height.facet', height.facet)
  //console.log('facet_ypos', facet_ypos)





  // Calculate height of each Scroll
  height.scrollFace = []
  height.facet.forEach(function(vScroll, iScroll){

    height.scrollFace[iScroll] = d3.sum(height.facetLabel[iScroll]) + ((yaxis.offset.top + yaxis.height + yaxis.offset.bottom)*height.facetLabel[iScroll].length)

  })
  //console.log('height.scrollFace:', height.scrollFace)



  // Canvas Height
  canvas.height = margin.top + height.title + height.scroll + height.switcher + height.legend + d3.max(height.scrollFace) + margin.bottom ;

  /*console.log('margin.top', margin.top)
  console.log('height.title', height.title)
  console.log('height.scroll', height.scroll)
  console.log('height.switcher', height.switcher)
  console.log('height.legend', height.legend)
  console.log('d3.max(height.scrollFace)', d3.max(height.scrollFace))
  console.log('margin.bottom', margin.bottom)
  console.log('canvas.height', canvas.height)*/







  // --- Donut properties --->

  // --- Calculate maximum text height taken up by radius labels (this helps define best outerRadius value) --->

  var max_SegmentLabelHeight = 0;
  if(segment_label.text != null){
    data.forEach(function(v, i, a){

          var segmentLabelHeight = 0;
          segment_label.text.forEach(function(vSegmentLabel, iSegmentLabel){
            var txt = '';

            vSegmentLabel['text'].forEach(function(vSegmentLineText, iSegmentLineText){
              txt = txt.concat(
                ((vSegmentLineText['prefix'] != null)?vSegmentLineText['prefix']:'') + ((vSegmentLineText['var'] != null)?((vSegmentLineText['format'] != null)? d3.format(vSegmentLineText['format'])(v[vSegmentLineText['var']]): v[vSegmentLineText['var']]): '') + ((vSegmentLineText['suffix'] != null)?vSegmentLineText['suffix']:'')
              )
            })

            var txt_split_wrap = splitWrapText(txt, yaxis.tick.width, fontSize=vSegmentLabel.size, fontWeight=vSegmentLabel.weight, fontFamily=font.family)

            txt_split_wrap.forEach(function(vSplitText, iSplitText){
              segmentLabelHeight += vSegmentLabel['size']*1.1
            })
          })

          max_SegmentLabelHeight = Math.max(max_SegmentLabelHeight, segmentLabelHeight)

    });
  }
  //console.log('max_SegmentLabelHeight:', max_SegmentLabelHeight)


  //var outerRadius = (Math.min(canvas.width, yaxis.height) / 2)*0.8;
  var outerRadius = Math.min(
    (yaxis.height - (max_SegmentLabelHeight*2))/2,
    (canvas.width - (margin.left + margin.right) - (yaxis.tick.width*2))/2
  );
  var innerRadius = outerRadius*inner_radius; // inner radius of pie, in pixels (non-zero for donut)
  //var labelRadius = outerRadius*1.1;

  var stroke = innerRadius > 0 ? "none" : "white";
  var strokeWidth = 1; // width of stroke separating segments
  var strokeLinejoin = "round"; // line join of stroke separating segments
  var padAngle = stroke === "none" ? 2 / outerRadius : 0; // angular separation between segments



  // --- Construct arcs --->

  //var arc = d3.arc().innerRadius(outerRadius*0.5).outerRadius(outerRadius*0.90);
  if(segment_label.text != null){
    var arc = d3.arc().cornerRadius(0).innerRadius((outerRadius*0.90)*inner_radius).outerRadius(outerRadius*0.90);

    var outer_width = outerRadius*0.90 - ((outerRadius*0.90)*inner_radius);
    var inner_circle_innerRadius = (((outerRadius*0.90)*inner_radius) + (outer_width*0.5)) - (outer_width*(inner_circle.width/2));
    var inner_circle_outerRadius = (((outerRadius*0.90)*inner_radius) + (outer_width*0.5)) + (outer_width*(inner_circle.width/2));

    var arcInner = d3.arc().innerRadius(inner_circle_innerRadius).outerRadius(inner_circle_outerRadius);
    var outerArc = d3.arc().innerRadius(outerRadius*0.95).outerRadius(outerRadius*0.95);

  }
  else{
    var arc = d3.arc().cornerRadius(0).innerRadius(innerRadius).outerRadius(outerRadius);

    var outer_width = outerRadius - innerRadius;
    var inner_circle_innerRadius = (innerRadius + (outer_width*0.5)) - (outer_width*(inner_circle.width/2));
    var inner_circle_outerRadius = (innerRadius + (outer_width*0.5)) + (outer_width*(inner_circle.width/2));

    var arcInner = d3.arc().innerRadius(inner_circle_innerRadius).outerRadius(inner_circle_outerRadius);
    var outerArc = d3.arc().innerRadius(innerRadius).outerRadius(outerRadius);

  }


  // <--- Construct arcs ---

  // <------------------------
  // <----- GRAPH SIZING -----
  // <------------------------










    // ---------------->
    // ----- DATA ----->
    // ---------------->

    var dataPlot = [];

    domainScroll.forEach(function(vScroll, iScroll){
      dataPlot[iScroll] = []

      domainFacet[iScroll].forEach(function(vFacet, iFacet){
        dataPlot[iScroll][iFacet] = [];

        domainSwitcher.forEach(function(vSwitcher, iSwitcher){
          dataPlot[iScroll][iFacet][iSwitcher] = [];

          //vFacet['y'].forEach(function(vY, iY){

            dataPlot[iScroll][iFacet][iSwitcher]['data'] = [];

            var endAngle = 0;
            var denominator = domainFacet[iScroll][iFacet]['maxValue'];

            domainGroup.forEach(function(vGroup, iGroup){

                var dataObs = data.filter(d => ((scroll.var != null)? d[scroll.var] == vScroll: true) && ((facet.var != null)? d[facet.var] == vFacet['facet']: true) && ((switcher.var != null)? d[switcher.var] == vSwitcher: true) && ((group.var != null)? d[group.var] == vGroup['group']: true) )[0]

                // Color of bar
                var newObs_clr;
                if(group.var != null){
                  dataObs_clr = (dataObs)? domainGroup.map(d => d['color'])[iGroup]: 'white';
                }
                else{
                  dataObs_clr = (clr.value != null)? clr.value: '#e32726';
                }

                var newObs = {
                  'switcher': vSwitcher,
                  'facet': (facet.var != null && dataObs)? dataObs[facet.var]: null,
                  'group': (group.var != null)? vGroup['group']: null,
                  'group_index': (group.var != null)? domainGroup.map(d => d['group']).indexOf(vGroup['group']): null,
                  'clr': dataObs_clr, //(clr.var != null)? ( (dataObs)? dataObs[clr.var]:'white') : ((clr.value != null)? clr.value: '#e32726'),

                  'denominator': denominator,
                  //'value': (dataObs)? dataObs[value.var]: 0,
                  'startAngle': endAngle,
                  'endAngle': (dataObs)? endAngle + ((dataObs[value.var]/denominator)*(2*Math.PI)): endAngle
                }

                newObs[value.var] = (dataObs)?dataObs[value.var]: null


                endAngle += (dataObs)? (dataObs[value.var]/denominator)*(2*Math.PI): 0;


                if(tooltip_text != null){
                  tooltip_text.forEach((v, i) => {
                      v['text'].forEach((v2, i2) => {
                        newObs[v2['var']] = (dataObs)?dataObs[v2['var']]: null
                      })
                  });
                }

                if(inner_text != null){
                  inner_text.forEach((v, i) => {
                      v['text'].forEach((v2, i2) => {
                        newObs[v2['var']] = (dataObs)?dataObs[v2['var']]: null
                      })
                  });
                }

                dataPlot[iScroll][iFacet][iSwitcher]['data'].push(newObs);
            })


            // ----- Construct arcs ----->
            var N = dataPlot[iScroll][iFacet][iSwitcher]['data'].map(d => d['group']);
            var V = dataPlot[iScroll][iFacet][iSwitcher]['data'].map(d => d[value.var]);
            var I = d3.range(N.length).filter(i => !isNaN(V[i]));

            dataPlot[iScroll][iFacet][iSwitcher]['arcs'] = d3.pie().padAngle(padAngle).sort(null).value(i => V[i])(I);
            //dataPlot[iScroll][iFacet][iSwitcher]['labels'] = i => `${d3.format(".1f")(V[i])}%`;

          //})
        })
      })
    })
    //console.log('### dataPlot', dataPlot);










    // ----- Change height of parent DIV ----->
    /*d3.select(html_id)
      .style('height', (canvas.height + 10) + 'px') ;*/

    // ----- Create SVG element ----->
    var svg = d3.select(html_id)
        .append("div")
        .classed("svg-container", true)
        .append("svg")
        .attr("preserveAspectRatio", "xMinYMin meet")
        .attr("viewBox", "0 0 " + canvas.width + " " + canvas.height)
        .classed("svg-content", true)
        .append('g');

        /*d3.select(html_id)
        .append("svg")
        .attr('width', canvas.width)
        .attr('height', canvas.height)
        //.attr("viewBox", [-canvas.width/2, -canvas.height/2, canvas.width, canvas.height])
        //.attr("style", "max-width: 100%; height: auto; height: intrinsic;");*/


        // Reference lines
        /*
        svg.selectAll('reference_lines')
          .data([
            0,
            margin.top,
            margin.top + height.title,
            margin.top + height.title + height.scroll,
            margin.top + height.title + height.scroll + height.switcher,
            margin.top + height.title + height.scroll + height.switcher + height.legend,
            margin.top + height.title + height.scroll + height.switcher + height.legend + yaxis.offset.top,
            margin.top + height.title + height.scroll + height.switcher + height.legend + yaxis.offset.top + yaxis.height,
            margin.top + height.title + height.scroll + height.switcher + height.legend + yaxis.offset.top + yaxis.height + yaxis.offset.bottom,
            margin.top + height.title + height.scroll + height.switcher + height.legend + yaxis.offset.top + yaxis.height + yaxis.offset.bottom + margin.bottom
          ])
          .enter()
          .append('path')
          .attr('d', d => 'M' + 0 + ',' + d + 'L' + canvas.width + ',' + d)
          .attr('stroke', 'red')
          .attr('stroke-width', '2');
          */



          /*console.log('margin.top', margin.top)
          console.log('height.title', height.title)
          console.log('height.scroll', height.scroll)
          console.log('height.switcher', height.switcher)
          console.log('height.legend', height.legend)
          console.log('d3.max(height.scrollFace)', d3.max(height.scrollFace))
          console.log('margin.bottom', margin.bottom)
          console.log('canvas.height', canvas.height)*/


    // ----------------->
    // ----- TITLE ----->
    // ----------------->

    // Group
    var g_title = svg.append('g')
      .attr('class', "g_title")
      .attr('transform', `translate(${margin.left}, ${margin.top})`);


    //  Title Text
    if(title.value != null){

        title.value.forEach(function(vTitle, iTitle){

          g_title.selectAll('title_text')
              .data(splitWrapText(vTitle.text, (canvas.width - margin.left - margin.right), fontSize=vTitle.size, fontWeight=vTitle.weight, fontFamily=font.family))
              .enter()
              .append('text')
                .style('font-family', font.family)
                .style('font-size', vTitle.size +  'px')
                .style('font-weight', vTitle.weight)
                .style('text-anchor', 'middle')
                .style('dominant-baseline', 'hanging')
                .attr('class', 'title_text_', iTitle)
                .attr('x', margin.left + ((canvas.width - margin.left - margin.right)/2))
                .attr('dy', function(d, i){ return i*1.1 + 'em' })
                .attr('transform', `translate(${0}, ${title_ypos[iTitle]})`)
                .text(d => d);

        })

        if(title.line){
            g_title.append('path')
              .attr('d', 'M' + 0 + ',' + (height.title - (margin.g/2)) + 'L' + (canvas.width - (margin.left + margin.right)) + ',' + (height.title - (margin.g/2)))
              .attr('stroke', '#d3d2d2')
              .attr('stroke-width', '2')
        }
    }

    // <-----------------
    // <----- TITLE -----
    // <-----------------










    // ------------------>
    // ----- SCROLL ----->
    // ------------------>

    // Group
    var g_scroll = svg.append('g')
      .attr('class', "g_scroll")
      .attr('transform', `translate(${margin.left}, ${margin.top + height.title})`);


    if(scroll.var != null){

      // Scroll Label
      if(scroll.label.value != null){
          g_scroll.selectAll('scroll_title')
              .data(splitWrapText(scroll.label.value, (canvas.width - margin.left - margin.right), fontSize=scroll.label.size, fontWeight=scroll.label.weight, fontFamily=font.family))
              .enter()
              .append('text')
                .attr('class', "scroll_title")
                .style('font-family', font.family)
                .style('font-size', scroll.label.size +  'px')
                .style('font-weight', scroll.label.weight)
                .style('text-anchor', 'middle')
                .style('dominant-baseline', 'hanging')
                .attr('x', (canvas.width - margin.left - margin.right)/2)
                .attr('dy', function(d, i){ return i*1.1 + 'em'})
                .text(d => d);
        }



        var maxScrollWidth = 0;

        domainScroll.forEach(function(vScroll, iScroll){

            var scrollData = splitWrapText(vScroll, (canvas.width - margin.left - margin.right - (scroll.size*2)), fontSize=scroll.size, fontWeight=scroll.weight, fontFamily=font.family)

            g_scroll.selectAll('scroll_text')
                .data(scrollData)
                .enter()
                .append('text')
                  .attr('class', "scroll_text_" + iScroll)
                  .attr('opacity', function(){ return 1 - Math.min(iScroll, 1) })
                  .style('font-family', font.family)
                  .style('font-size', scroll.size +  'px')
                  .style('font-weight', scroll.weight)
                  .style('text-anchor', 'middle')
                  .style('dominant-baseline', 'hanging')
                  .attr('x', (canvas.width - margin.left - margin.right)/2)
                  .attr('transform', `translate(${(Math.min(iScroll, 1)*canvas.width)}, ${height.scrollLabel})`)
                  .attr('dy', function(d, i){ return i*1.1 + 'em'})
                  .text(d => d);


            scrollData.forEach(function(vScroll2, iScroll2){
              maxScrollWidth = (textWidth(vScroll2, fontSize=scroll.size, fontWeight=scroll.weight, fontFamily=font.family) > maxScrollWidth)? textWidth(vScroll2, fontSize=scroll.size, fontWeight=scroll.weight, fontFamily=font.family): maxScrollWidth;
            })
        });


        var scrollIndex = 0;

        g_scroll.append('path')
              .attr('class', "scroll_right")
              .attr('d', 'M' + (canvas.width - (margin.left + margin.right))/2 + ',' + (height.scrollLabel) + 'L' + (canvas.width - (margin.left + margin.right))/2 + ',' + ((height.scrollLabel) + (height.scroll-margin.g-height.scrollLabel)) + 'L' + (((canvas.width - (margin.left + margin.right))/2)-scroll.size) + ',' + ((height.scrollLabel) + (height.scroll-margin.g-height.scrollLabel)/2) + 'L' + ((canvas.width - (margin.left + margin.right))/2) + ',' + (height.scrollLabel))
              .attr('stroke', "#d3d2d2")
              .attr('fill', "#d3d2d2")
              .attr('transform', `translate(${-((maxScrollWidth/2) + 20)}, ${0})`)
              .on('click', function(event){
                scrollChart('down')
              })
              .on("mouseover", function(d) {
                  d3.select(this).style("cursor", "pointer");
              });


        g_scroll.append('path')
              .attr('class', "scroll_right")
              .attr('d', 'M' + (canvas.width - (margin.left + margin.right))/2 + ',' + (height.scrollLabel) + 'L' + (canvas.width - (margin.left + margin.right))/2 + ',' + ((height.scrollLabel) + (height.scroll-margin.g-height.scrollLabel)) + 'L' + (((canvas.width - (margin.left + margin.right))/2)+scroll.size) + ',' + ((height.scrollLabel) + (height.scroll-margin.g-height.scrollLabel)/2) + 'L' + ((canvas.width - (margin.left + margin.right))/2) + ',' + (height.scrollLabel))
              .attr('stroke', "#d3d2d2")
              .attr('fill', "#d3d2d2")
              .attr('transform', `translate(${((maxScrollWidth/2) + 20)}, ${0})`)
              .on('click', function(event){
                scrollChart('up')
              })
              .on("mouseover", function(d) {
                  d3.select(this).style("cursor", "pointer");
              });


        if(scroll.line){
            g_scroll.append('path')
              .attr('d', 'M' + 0 + ',' + (height.scroll - (margin.g/2)) + 'L' + (canvas.width - (margin.left + margin.right)) + ',' + (height.scroll - (margin.g/2)))
              .attr('stroke', '#d3d2d2')
              .attr('stroke-width', '2')
        }

    }

    // <------------------
    // <----- SCROLL -----
    // <------------------










    // -------------------->
    // ----- SWITCHER ----->
    // -------------------->

    // Group
    var g_switcher = svg.append('g')
      .attr('class', "g_switcher")
      .attr('transform', `translate(${canvas.width/2}, ${margin.top + height.title + height.scroll})`);

    if(switcher.var != null){

      // Switcher Label
      if(switcher.label.value != null){
          g_switcher.selectAll('switch_title')
              .data(splitWrapText(switcher.label.value, (canvas.width - margin.left - margin.right), fontSize=switcher.label.size, fontWeight=switcher.label.weight, fontFamily=font.family))
              .enter()
              .append('text')
                .attr('class', "switcher_title")
                .style('font-family', font.family)
                .style('font-size', switcher.label.size +  'px')
                .style('font-weight', switcher.label.weight)
                .style('text-anchor', 'middle')
                .style('dominant-baseline', 'hanging')
                .attr('x', 0)
                .attr('dy', function(d, i){ return i*1.1 + 'em'})
                .text(d => d);
        }



      var switcherGroup = g_switcher.selectAll('.switcher')
          .data(switcherText)
          .enter()
          .append('g')
            .attr('class', function(d, i){ return "switcher switcher_" + i})
            .attr('transform', function(d){ return `translate(${d['x']}, ${(d['y'] + height.switcherLabel)})` })
            .attr('opacity', function(d, i){
              if(i == 0){ return 1.0 }
              else{ return 0.2 }
            })
            .on('click', (event, v) => {

                  svg.selectAll('.switcher').attr('opacity', 0.2);
                  svg.select('.' + event.currentTarget.getAttribute('class').split(' ')[1]).attr('opacity', 1.0);

                  changeBars(event.currentTarget.getAttribute('class').split(' ')[1].split('_')[1] )

            })
            .on("mouseover", function(d) {
                d3.select(this).style("cursor", "pointer");
            });


      switcherGroup.append("rect")
        .attr('class', function(d, i){ return "switcher_" + i})
        .attr('width-value', d => d['width-value'])
        //.attr('x', d => 0 - (d['width-value']/2))
        //.attr('x', -5)
        .attr('x', 5)
        .attr('y', -3)
        .attr('width', d => d['width-value']-8)
        .attr('height', d => (d['text'].length*(switcher.size*1.1)) + 6)
        .attr('fill', '#d3d2d2');


      switcherGroup.append('text')
        .attr('class', function(d, i){ return "switcher_" + i})
        .style('font-family', font.family)
        .style('font-size', switcher.size +  'px')
        .style('font-weight', switcher.weight)
        //.style('text-anchor', "start")
        .style('text-anchor', 'middle')
        .style('dominant-baseline', 'hanging')
        .attr('width-value', d => d['width-value'])
        .attr('x', 0)
        .each(function(d, i){
          d3.select(this).selectAll('.switcher_text_' + i)
            .data(d['text'])
            .enter()
            .append('tspan')
            //.attr('x', d => (d['max-width-value'] - d['this-width-value'])/2) // Centre-align horizontally
            .attr('x', d => d['max-width-value']/2) // Centre-align horizontally
            .attr('dy', d => d['dy'])
            .text( d => d['value'])
        });


      if(switcher.line){
          g_switcher.append('path')
            .attr('d', 'M' + 0 + ',' + (height.switcher - (margin.g/2)) + 'L' + (canvas.width - (margin.left+margin.right)) + ',' + (height.switcher - (margin.g/2)))
            .attr('stroke', '#d3d2d2')
            .attr('stroke-width', '2')
            .attr('transform', function(d){ return `translate(${(-(canvas.width/2)+margin.left)}, ${0})` })

      }
    }

    // <--------------------
    // <----- SWITCHER -----
    // <--------------------










    // ------------------>
    // ----- LEGEND ----->
    // ------------------>

    // Group
    var g_legend = svg.append('g')
      .attr('class', "g_legend")
      .attr('transform', `translate(${canvas.width/2}, ${margin.top + height.title + height.scroll + height.switcher})`);


    if(group.var != null && (group.show == undefined || group.show)){
        // Legend Label
        if(group.label.value != null){
            g_legend.selectAll('legend_title')
                .data(splitWrapText(group.label.value, (canvas.width - margin.left - margin.right), fontSize=group.label.size, fontWeight=group.label.weight, fontFamily=font.family))
                .enter()
                .append('text')
                  .attr('class', "legend_title")
                  .style('font-family', font.family)
                  .style('font-size', group.label.size +  'px')
                  .style('font-weight', group.label.weight)
                  .style('text-anchor', 'middle')
                  .style('dominant-baseline', 'hanging')
                  .attr('x', 0)
                  .attr('dy', function(d, i){ return i*1.1 + 'em'})
                  .text(d => d);
        }

        var legend = g_legend.selectAll('.legend')
            .data(legendText)
            .enter()
            .append('g')
              .attr('class', function(d, i){ return "legend_" + i})
              //.attr('transform', function(d){ return `translate(${d['x']}, ${d['y']})` })
              .attr('transform', function(d){ return `translate(${d['x']}, ${(d['y'] + height.legendLabel)})` })
              .attr('opacity', 1.0)
              .on('click', (event, v) => {

                    if(+event.currentTarget.getAttribute('opacity') == 1){
                        svg.select('.' + event.currentTarget.getAttribute('class')).attr('opacity', 0.2);
                        //svg.selectAll('.group_' + event.currentTarget.getAttribute('class').split('_')[1]).transition().duration(200).attr('opacity', 0);
                        svg.selectAll('.group_' + event.currentTarget.getAttribute('class').split('_')[1]).transition().duration(200).attr('visibility', 'hidden');
                    }
                    else{
                        svg.select('.' + event.currentTarget.getAttribute('class')).attr('opacity', 1.0);
                        //svg.selectAll('.group_' + event.currentTarget.getAttribute('class').split('_')[1]).transition().duration(200).attr('opacity', 1);
                        svg.selectAll('.group_' + event.currentTarget.getAttribute('class').split('_')[1]).transition().duration(200).attr('visibility', 'visible');
                        //svg.selectAll('.group_' + event.currentTarget.getAttribute('class').split('_')[1]).filter('.bar_rect').transition().duration(200).attr('opacity', d => d['opacity']);
                    }

              })
              .on("mouseover", function(d) {
                  d3.select(this).style("cursor", "pointer");
              });


        legend.append('rect')
          .attr('class', function(d, i){ return "legend_" + i})
          .attr('x', 0)
          .attr('width', group.size)
          .attr('height', group.size)
          .attr('fill', d => d['color'])
          .attr('stroke-width', 1)
          .attr('stroke', function(d){
            if(d['color'] == 'white' || d['color'] == 'rgb(255,255,255)' || d['color'] == '#fff' || d['color'] == '#ffffff'){
              return '#d3d2d2'
            }
            else{
              return d['color']
            }
          });

        legend.append('text')
          .attr('class', function(d, i){ return "legend_" + i})
          .style('font-family', font.family)
          .style('font-size', group.size +  'px')
          .style('font-weight', group.weight)
          .style('text-anchor', "start")
          .style('dominant-baseline', 'hanging')
          .attr('width-value', d => d['width-value'])
          .attr('x', group.size + 5)
          .each(function(d, i){
            d3.select(this).selectAll('.legend_text_' + i)
              .data(d['text'])
              .enter()
              .append('tspan')
              .attr('x', group.size + 5)
              .attr('dy', d => d['dy'])
              .text( d => d['value'])
          });
    }

    // <------------------
    // <----- LEGEND -----
    // <------------------









    // ----------------->
    // ----- CHART ----->
    // ----------------->

    dataPlot.forEach(function(vScroll, iScroll){

        // ----- Group ----->
        var g_scroll = svg.append('g')
          .attr('class', "g_chart g_scroll_" + iScroll)
          .attr('opacity', d => 1 - Math.min(iScroll, 1))
          .attr('x', canvas.width*iScroll)
          .attr('transform', function(d, i){
            return `translate(${((canvas.width*Math.min(1, iScroll)) + margin.left)}, ${margin.top + height.title + height.scroll + height.switcher + height.legend})`
          });
        // <----- Group -----





        vScroll.forEach(function(vFacet, iFacet){

          var g_facet = g_scroll.append('g')
            .attr('class', 'facet_' + iFacet)
            .attr('transform', `translate(${((canvas.width-(margin.left + margin.right))/2)}, ${facet_ypos[iScroll][iFacet]})`)




          // --- Add line above Facet --->
          if(facet.line.show){
            g_facet.append('path')
              .attr('d', 'M' + margin.yaxisLabel[iScroll] + ',' + (-height.facetLabel[iScroll][iFacet] + (facet.space_above_title/2)) + 'L' + (canvas.width - (margin.left + margin.right)) + ',' + (-height.facetLabel[iScroll][iFacet] + (facet.space_above_title/2)))
              .attr('stroke', (facet.line.color != null)? facet.line.color: 'black')
              .attr('stroke-width', '2')
          }
          // <--- Add line above Facet ---





          // --- Facet Title --->
          if(facet.var != null){

            g_facet.selectAll('facet_text')
                .data(splitWrapText(domainFacet[iScroll][iFacet]['facet'], (canvas.width - margin.left - margin.yaxisLabel[iScroll] - margin.right), fontSize=facet.size, fontWeight=facet.weight, fontFamily=font.family))
                .enter()
                .append('text')
                  .style('font-family', font.family)
                  .style('font-size', facet.size +  'px')
                  .style('font-weight', facet.weight)
                  .style('text-anchor', 'middle')
                  .style('dominant-baseline', 'hanging')
                  .attr('class', "facet_text")
                  .attr('x', margin.yaxisLabel[iScroll] + ((canvas.width - margin.left - margin.yaxisLabel[iScroll] - margin.right)/2))
                  .attr('dy', function(d, i){ return i*1.1 + 'em'})
                  .attr('transform', `translate(${0}, ${-height.facetLabel[iScroll][iFacet] + facet.space_above_title})`)
                  .text(d => d);

          }
          // <--- Facet Title ---





          // --- Add Donut --->
          // Arcs
          var g_segments = g_facet.append('g')
            .attr('style', 'g_segment')
            .attr('transform', `translate(${0}, ${0 + yaxis.offset.top + (yaxis.height/2)})`)

          // inner Arc
          if(inner_circle.show){
            g_segments.selectAll(".inner_path")
              .data([{'startAngle': 0, 'endAngle':2*Math.PI}])
                .enter()
                .append("path")
                .attr('stroke', stroke)
                .attr('stroke-width', strokeWidth)
                .attr('stroke-linejoin', strokeLinejoin)
                .attr('fill', (inner_circle.clr != null)? inner_circle.clr: '#d3d2d2') // light gray
                .attr('d', arcInner);
          }


          //vFacet[0]['data'].forEach(function(vObs, iObs){

          var g_data = g_segments.selectAll('.donut_arc')
            .data(vFacet[0]['data'])
            .enter()
            .append('g')
              .attr('class', function(d, i){
                return 'scroll_' + iScroll +
                ' switcher_0' +
                ' facet_' + iFacet +
                ' group_' + domainGroup.map(d => d['group']).indexOf(d['group']) +
                ' obs_' + iScroll + '_0_' + iFacet + '_' + domainGroup.map(d => d['group']).indexOf(d['group']) + '_' + i
              })
              .attr('startAngle', d => d['startAngle'])
              .attr('endAngle', d => d['endAngle'])
              .attr('color-value', d => d['clr'])
              .attr('group-value', function(d){
                if(group.var != null){ return d['group'] }
                else{ return null }
              })
              .attr('value', d => d[value.var])
              .attr('opacity', 1.0)
              .attr('visibility', 'visible')
              .on('mouseover', (event, d) => {

                  if(event.currentTarget.getAttribute('visibility') == 'visible'){

                        // --- Tooltip --->
                        var facetIndex = +event.currentTarget.getAttribute('class').split(' ')[2].split('_')[1]
                        var thisStartAngle = +event.currentTarget.getAttribute('startAngle')
                        var thisEndAngle = +event.currentTarget.getAttribute('endAngle')

                        var midAngle = thisStartAngle + ((thisEndAngle - thisStartAngle)/2);
                        var angle = (midAngle/(Math.PI * 2))*360 //(midAngle*360)/(Math.PI * 2);
                        var thisX = ((outerRadius*1.00) * Math.sin(Math.PI * 2 * angle / 360)) + (canvas.width/2);
                        var thisY = ((margin.top + height.title + height.scroll + height.switcher + height.legend) + (yaxis.offset.top) + (yaxis.height/2)) -((outerRadius*1.00) * Math.cos(Math.PI * 2 * angle / 360));
                        thisY += facet_ypos[facetIndex]
                        /*console.log(
                          'facetIndex:', facetIndex,
                          'thisEndAngle:', thisEndAngle,
                          'thisStartAngle:', thisStartAngle,
                          'midAngle:', midAngle,
                          'angle:', angle,
                          'thisX:', thisX,
                          'thisY:', thisY
                        )*/

                        //svg.append('circle').attr('cx', thisX).attr('cy', thisY).attr('r', 3).attr('fill', 'red')



                        var maxTextWidth = 0;
                        var rectHeight = 0;
                        var hoverText = [];


                        if(tooltip_text != null){
                          var scrollIndex = event.currentTarget.getAttribute('class').split(' ')[0].split('_')[1]
                          var facetIndex = event.currentTarget.getAttribute('class').split(' ')[2].split('_')[1]
                          var switcherIndex = event.currentTarget.getAttribute('class').split(' ')[1].split('_')[1]
                          var obsIndex = event.currentTarget.getAttribute('class').split(' ')[4].split('_')[5]

                          thisY += facet_ypos[scrollIndex][facetIndex]

                          var dataPoint = dataPlot[scrollIndex][facetIndex][switcherIndex]['data'][obsIndex]

                          tooltip_text.forEach(function(vTooltipLine, iTooltipLine, aTooltipLine){
                            var val = '';
                            rectHeight += (vTooltipLine.size*1.1);

                            vTooltipLine['text'].forEach(function(vTooltipLineText, iTooltipLineText){
                              val = val.concat(
                                ((vTooltipLineText['prefix'] != null)?vTooltipLineText['prefix']:'') + ((vTooltipLineText['var'] != null)?((vTooltipLineText['format'] != null)? d3.format(vTooltipLineText['format'])(dataPoint[vTooltipLineText['var']]): dataPoint[vTooltipLineText['var']]): '') + ((vTooltipLineText['suffix'] != null)?vTooltipLineText['suffix']:'')
                              )
                            })
                            maxTextWidth = (textWidth(val, vTooltipLine.size, vTooltipLine.weight) > maxTextWidth)? textWidth(val, vTooltipLine.size, vTooltipLine.weight): maxTextWidth;

                            hoverText.push({
                              'value': val.replace('<br>', ' ').replace('\n', ' '),
                              'size': vTooltipLine.size,
                              'weight': vTooltipLine.weight
                            });
                          })
                        }
                        else{
                          hoverText.push(event.currentTarget.getAttribute('x-value'));

                          rectHeight += (14*1.1);
                          maxTextWidth = (textWidth(event.currentTarget.getAttribute('x-value'), 14, yaxis.tick.weight) > maxTextWidth)? textWidth(event.currentTarget.getAttribute('x-value'), 14, yaxis.tick.weight): maxTextWidth;
                        }




                        if((thisX + (maxTextWidth*0.5) + 5) > (canvas.width - margin.right)){
                          var shift_left = Math.abs((canvas.width - margin.right) - (thisX + (maxTextWidth*0.5) + 5))
                        };

                        g_tooltip.style('opacity', 1)
                            .attr('transform', `translate(${(thisX-(shift_left || 0))}, ${(thisY-rectHeight-3)})`)

                        tooltipRect.attr('stroke', function(){
                            if(event.currentTarget.getAttribute('color-value') == 'white' || event.currentTarget.getAttribute('color-value') == 'rgb(255,255,255)' || event.currentTarget.getAttribute('color-value') == '#fff' || event.currentTarget.getAttribute('color-value') == '#ffffff'){
                              return '#d3d2d2'
                            }
                            else{
                              return event.currentTarget.getAttribute('color-value')
                            }
                          })
                          .attr('width', maxTextWidth + 20)
                          .attr('height', rectHeight+6)
                          .attr('x', -((maxTextWidth + 20)*0.5));

                        tooltipText.selectAll('tspan').remove();

                        var dy = 0;
                        hoverText.forEach(function(vHover, iHover){
                          tooltipText.append('tspan')
                              .style('font-size', vHover['size'])
                              .style('font-weight', vHover['weight'])
                              .attr('x', 0)
                              .attr('y', 0)
                              .attr('dy', dy + 'px')
                              .text(vHover['value']);

                          dy += 1.1*vHover['size'];
                        })

                        // <--- Tooltip ---

                    }


              })
              /*.on('mousemove', (event, v) => {

                    const x = event.layerX; //event.pageX;
                    const y = event.layerY; //event.pageY;


                    g_tooltip.attr('transform', `translate(${x+20}, ${y})`);
              })*/
              .on('mouseout', (event, v) => {
                      g_tooltip.style('opacity', 0).attr('transform', "translate(" + 0 + "," + 0 +")");
              });




          // Donut Arcs
          g_data.append("path")
              //.attr('class', 'arc_path')
              .attr('class', function(d){
                return 'arc_path_' + iScroll + '_' + iFacet + '_' + domainGroup.map(d => d['group']).indexOf(d['group']) + '_' + '0' +
                ' group_all group_' + domainGroup.map(d => d['group']).indexOf(d['group']) +
                ' arc_path'
              })
              //.attr('stroke', stroke)
              //.attr('stroke-width', strokeWidth)
              .attr('stroke-linejoin', strokeLinejoin)
              .attr('stroke-width', strokeWidth)
              .attr('stroke', function(d){
                if(d['clr'] == 'white' || d['clr'] == 'rgb(255,255,255)' || d['clr'] == '#fff' || d['clr'] == '#ffffff'){
                  return '#d3d2d2'
                }
                else{
                  return 'white' //d['clr']
                }
              })
              //.transition().delay(function (d, i) { return i*800}).duration(800)
              //.attrTween('d', arcTween)
              //.attr('fill', '#ffffff')
              .attr('fill', d => d['clr'])
              .attr('startAngle', d => d['startAngle'])
              .attr('endAngle', d => d['endAngle'])
              //.attr('d', arc)
              .style('cursor', 'pointer')
              .style('opacity', '1')
              .transition()
                  .delay(function(d, i){
                    return 1000*(d['startAngle']/(2*Math.PI))
                    //return 0;
                  })
                  .duration(function(d, i){
                    return 1000*(d[value.var]/d['denominator'])
                    //return 1000*(d[pct_var]/100)
                    //return (d.value/tot)*1000;
                    //return 1000;
                  })
                  //.style('opacity', '1.0')
                  //.attr('fill', d => colorScale(V[d[name_var]]))
                  .attrTween('d', function (d) {
                      var start = {
                        startAngle: d['startAngle'],
                        endAngle: d['startAngle']
                      }
                      var end = d // {startAngle: -0.5 * Math.PI, endAngle: 0.5 * Math.PI}
                      var interpolate = d3.interpolate(start, end); // <-B
                      return function (t) {
                          return arc(interpolate(t)); // <-C
                      };
                  });







        // -------------------------->
        // ----- Segment Labels ----->
        // -------------------------->

        // Function to find middle of an arc
        function midAngle(d){
          return d.startAngle + (d.endAngle - d.startAngle)/2;
        }

        if(segment_label.text != null){


            // --- Line from segment to text --->

            var polyline = g_segments.append('g')
              .attr('class', 'lines')
              .selectAll('polyline')
              //.data(vFacet[0]['data'].filter(d => (d['endAngle'] - d['startAngle']) > 0.25));
              .data(vFacet[0]['data'].filter(d => (d['endAngle'] - d['startAngle']) > (segment_label.minValue*(Math.PI*2))) );


            polyline.enter()
              .append('polyline')
              .attr('class', d => "label_line group_" + d['group_index'])
              .style('fill', 'none').style('stroke', 'white');

            svg.selectAll('.label_line').transition().delay(1000).duration(200)
              .style('stroke', 'black')
              .attrTween("points", function(d){
                this._current = this._current || d;
                var interpolate = d3.interpolate(this._current, d);
                this._current = interpolate(0);
                return function(t) {
                  var d2 = interpolate(t);
                  var pos = outerArc.centroid(d2);
                  pos[0] = (outerRadius * 0.95) * (midAngle(d2) < Math.PI ? 1 : -1);

                  return [arc.centroid(d2), outerArc.centroid(d2), outerArc.centroid(d2)];
                };
              });

            // <--- Lines from segment to text ---



            // --- Labels around edge of circle --->
            vFacet[0]['data'].forEach(function(v, i, a){

              //if((v['endAngle'] - v['startAngle']) > 0.25){
              if((v['endAngle'] - v['startAngle']) > (segment_label.minValue*(Math.PI*2)) ){

                  var g_segment_label = g_segments.append('g')
                    .attr('class', 'segment_label_' + i + ' group_' + v['group_index'])
                    .attr('opacity', 0.0);


                  var angle = v['startAngle'] + (v['endAngle'] - v['startAngle'])/2; //360*(domainFacet[iScroll][iFacet]['y'].indexOf(v) / domainFacet[iScroll][iFacet]['y'].length);
                  var radius = outerRadius*1.00;

                  //var x = radius * Math.sin(Math.PI * 2 * angle / 360);
                  //var y = -(radius * Math.cos(Math.PI * 2 * angle / 360));
                  var x = radius * Math.sin(v['startAngle'] + (v['endAngle'] - v['startAngle'])/2);
                  var y = -(radius * Math.cos(v['startAngle'] + (v['endAngle'] - v['startAngle'])/2));

                  var segmentLabelText = [];
                  var maxSize = 0
                  segment_label.text.forEach(function(vSegmentLabel, iSegmentLabel){
                    var txt = '';

                    vSegmentLabel['text'].forEach(function(vSegmentLineText, iSegmentLineText){
                      txt = txt.concat(
                        ((vSegmentLineText['prefix'] != null)?vSegmentLineText['prefix']:'') + ((vSegmentLineText['var'] != null)?((vSegmentLineText['format'] != null)? d3.format(vSegmentLineText['format'])(v[vSegmentLineText['var']]): v[vSegmentLineText['var']]): '') + ((vSegmentLineText['suffix'] != null)?vSegmentLineText['suffix']:'')
                      )
                    })

                    var txt_split_wrap = splitWrapText(txt, yaxis.tick.width, fontSize=vSegmentLabel.size, fontWeight=vSegmentLabel.weight, fontFamily=font.family)

                    txt_split_wrap.forEach(function(vSplitText, iSplitText){
                      segmentLabelText.push({
                        'text':vSplitText,
                        'size': vSegmentLabel['size'],
                        'weight': vSegmentLabel['weight'],
                      })

                      maxSize += vSegmentLabel['size']*1.1
                    })
                  })


                  var dy = 0;
                  segmentLabelText.forEach(function(v2, i2, a2){

                    g_segment_label.append('text')
                      .attr('x', x)
                      //.attr('y', y + (((((v2['size']*1.1)*a2.length))/a2.length)*i2) )
                      .attr('y', y + dy)
                      .style('text-anchor', function(d){
                         if(Math.round(x) == 0){ return 'middle'}
                         else if (x > 0){ return 'start'}
                         else{ return 'end'}
                      })
                      .style('alignment-baseline', 'hanging')
                      .style('font-family', font.family)
                      .style('font-size', v2['size'] + 'px')
                      .style('font-weight', v2['weight'])
                      .text(v2['text']);

                    dy += v2['size']*1.1;


                  });

                  var angle = (angle/(Math.PI * 2))*360;

                  if(angle < 90 || angle > 270){
                    g_segment_label.attr('transform', `translate(${0}, ${-(maxSize)})`);
                  }
                  if(Math.round(angle) == 90 || Math.round(angle) == 270){
                    g_segment_label.attr('transform', `translate(${0}, ${-(maxSize/2)})`);
                  }

                  svg.selectAll('.segment_label_' + i)
                      .transition()
                      .delay(1000)
                      .duration(200)
                        .attr('opacity', 1.0)

              }

            });

        }

        // <--------------------------
        // <----- Segment Labels -----
        // <--------------------------





        // ----------------------------------->
        // ----- Text in centre of graph ----->
        // ----------------------------------->

        if(inner_text != null){

          var innerTextHeight = 0;
          inner_text.forEach(function(vInner, iInner, aInner){
            innerTextHeight += vInner['size']*1.1
          })

          var prevTotalHeight = 0;
          inner_text.forEach(function(vInner, iInner, aInner){

            var txt = '';
            vInner['text'].forEach(function(vInnerText, iInnerText){

              if(vInnerText['var'] != null && vInnerText['aggregate'] != null){

                     if(vInnerText['aggregate'] == 'sum'   ){ var aggVal = d3.format(vInnerText['format'])(d3.sum(vFacet[0]['data'].map(d => d[vInnerText.var]))) }
                else if(vInnerText['aggregate'] == 'min'   ){ var aggVal = d3.format(vInnerText['format'])(d3.min(vFacet[0]['data'].map(d => d[vInnerText.var]))) }
                else if(vInnerText['aggregate'] == 'max'   ){ var aggVal = d3.format(vInnerText['format'])(d3.max(vFacet[0]['data'].map(d => d[vInnerText.var]))) }
                else if(vInnerText['aggregate'] == 'mean'  ){ var aggVal = d3.format(vInnerText['format'])(d3.mean(vFacet[0]['data'].map(d => d[vInnerText.var]))) }
                else if(vInnerText['aggregate'] == 'median'){ var aggVal = d3.format(vInnerText['format'])(d3.median(vFacet[0]['data'].map(d => d[vInnerText.var]))) }
              }
              else{
                var aggVal = ''
              }



              txt = txt.concat(
                ((vInnerText['prefix'] != null)?vInnerText['prefix']:'') + aggVal + ((vInnerText['suffix'] != null)?vInnerText['suffix']:'')
              )


            })



            g_segments.append('g')
              .append('text')
                .style('font-family', font.family)
                .style('font-size', vInner['size'])
                .style('font-weight', vInner['weight'])
                .style('text-anchor', 'middle')
                .style('dominant-baseline', 'hanging')
                .attr('transform', d => `translate(0, ${-(innerTextHeight/2)})`)
              .append('tspan')
                .attr('x', 0)
                .attr('y', prevTotalHeight)
                .text(txt);

            prevTotalHeight += vInner['size']*1.1
          })

        }

        // <-----------------------------------
        // <----- Text in centre of graph -----
        // <-----------------------------------





        })
      });

  // <-----------------
  // <----- CHART -----
  // <-----------------










  // ------------------->
  // ----- TOOLTIP ----->
  // ------------------->

  var g_tooltip = svg.append('g')
    .attr('class', "tooltip_" + html_id.slice(1))
    .style('opacity', 0);

  var tooltipRect =  g_tooltip.append('rect')
      .attr('class', "tooltip_" + html_id.slice(1) + "__rect")
      .attr('x', 0)
      .attr('y', -3)
      .attr('width', 0)
      .attr('height', 0)
      .attr('fill', "white")
      .attr('stroke', "black")
      .attr('stroke-width', "2");

  var tooltipText = g_tooltip.append('text')
    .style('text-anchor', 'middle')
    .style('dominant-baseline', 'hanging')
    .attr('class', "tooltip_" + html_id.slice(1) + "__text")
    .style('font-family', font.family)
    .attr('x', 0)
    .attr('y', 0)

  // <-------------------
  // <----- TOOLTIP -----
  // <-------------------





  // ---------------------->
  // ----- Zoom & Pan ----->
  // ---------------------->
  if(zoom){
    let zoomChart = d3.zoom()
      .on('zoom', handleZoom)
      .scaleExtent([0.5, 1])
      .translateExtent([[0, 0], [canvas.width, canvas.height]]);

    function handleZoom(e) {
      d3.select(html_id + ' svg g')
        .attr('transform', e.transform);
    }

    d3.select(html_id + ' svg')
      .call(zoomChart);
  }
  // <----------------------
  // <----- Zoom & Pan -----
  // <----------------------
}
