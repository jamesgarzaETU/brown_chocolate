// ----- Function to show text from a Decision Level in a div ----->
function text_sim_decisions(
  data,
  html_id2,
  title,
  font={'family':null, 'title':{'size':40, 'weight':700}, 'axis':{'tick':{'size':16, 'weight':400}, 'label':{'size':20, 'weight':700}}}
){

  d3.select(html_id2).selectAll('div').remove();

  d3.select(html_id2)
    .append('div')
      .attr('class', 'card card_graph')
      .attr('id', html_id2.substring(1) + '_text')
      .style('display', 'block')


  var table_title = d3.select(html_id2 + '_text').append('h2').style('text-align', 'center').style('color', 'black').style('font-weight', '700').text(title);
  var table = d3.select(html_id2 + '_text').append('table').style('text-align', 'left').style('border', '1px solid white').style('border-collapse', 'separate').style('border-spacing', '2px');
  var thead = table.append('thead')
  var	tbody = table.append('tbody');
  var columns = ['', 'Text', 'Coach Feedback'];

  // append the header row
  thead.append('tr')
    .selectAll('th')
    .data(columns)
    .enter()
    .append('th')
      .style('background', '#d3d2d2')
      .style('padding-left', '20px')
      .style('padding-right', '10px')
      .style('padding-top', '5px')
      .style('padding-bottom', '5px')
      .text(function (column) { return column; });

  // create a row for each object in the data
  var rows = tbody.selectAll('tr')
    .data(data.map(d => [d['category'], d['text'], d['coaching'], d['bg_color'], d['font_color']]) )
    .enter()
    .append('tr')
      .attr('valign', 'top');


  // create a cell in each row for each column
  var cells = rows.selectAll('td')
    .data(function (row) {
      return columns.map(function (column, i) {
        bg_color = row[3]; //(i <= 1)?row[3] :'white';
        font_color = row[4]; //(i <= 1)?row[4] :'black';
        return {'column': column, 'value': row[i], 'bg_color': bg_color, 'font_color': font_color};
      });
    })
    .enter()
    .append('td')
      .style('padding-left', '10px')
      .style('padding-right', '10px')
      .style('padding-top', '0px')
      .style('padding-bottom', '0px')
      .style('background', function(d){
        return d['bg_color'];
        //if(d.value == "Optimal"){ return '#339933' }
        //else if(d.value == "Suboptimal"){ return '#ffb833' }
        //else if(d.value == "Critical"){ return '#e32726' }
        //else{ return 'white'}
      })
      .style('color', function(d){
        return d['font_color'];
        //if(d.value == "Optimal"){ return 'white' }
        //else if(d.value == "Suboptimal"){ return 'black' }
        //else if(d.value == "Critical"){ return 'white' }
        //else{ return 'black'}
      })
      .html(function (d) {
        return d['value'];
      });
      //.text(function (d) {
      //  return d['value'];
      //});


  d3.selectAll('.user-select-none')
    //.style("height", 270 + 'px')
    .style("overflow", 'hidden');

};

// <----- Function to show text from a Decision Level in a div -----





function chart_sim_decisions(
  data,
  data_skills,
  html_id,
  x={var:null}, // Must be numeric
  y={var:null, order:'as_appear'}, // Must be categorical

  title={value:null, size:40, weight:700, line:false},

  clr_var='clr', // Variable containing color of bar(s)

  skill = {var:'skillname'},
  facet = {var:null, size:18, weight:400, order:'as_appear'},
  group = {var:null, label:{value:null, size:18, weight:700}, size:18, weight:400, order:'as_appear'},
  switcher = {var:null, label:{value:null, size:18, weight:700}, size:18, weight:400, order:'as_appear', line:false},
  scroll = {var:null, label:{value:null, size:20, weight:700}, size:18, weight:400, order:'as_appear', line:false},

  bar={
    text:null, // Array of arrays: [{'var':'n', 'format':',', 'prefix':null, 'suffix':null}, {'var':'pct', 'format':'.1f', 'prefix':null, 'suffix':'%'}]
    extra_height:0,
    height:{var:null}
  },

  tooltip_text=[
    {size:14, weight:400, text:[{var:'pct', format:'.1f', prefix:null, suffix:'%'}]},
    {size:14, weight:400, text:[
      {var:'n', format:',.0f', prefix:null, suffix:null},
      {var:'tot', format:',.0f', prefix:'/', suffix:null}
    ]}
  ],

  barmode='group', // 'group' or 'stack'

  xaxis={
    'range': [null, null],
    'suffix': null,
    'tick':{'size':14, 'weight':400},
    'label':{'value':null, 'size':20, 'weight':700},
    'offset': {'left':10, 'right':10},
    'show':true,
    'show_line':true,
    'show_ticks':true,
    'num_ticks':null,
    'show_grid':false
  },

  yaxis={
    'tick':{'size':16, 'weight':400},
    'label':{'value':null, 'size':20, 'weight':700},
    'offset': {'top':10, 'bottom':10},
    'show':true,
    'show_line':true,
    'show_ticks':true,
    'order': 'as_appear' // 'as_appear' or 'alphabetical'
  },

  font={'family':'Catamaran'},

  margin={'top':10, 'bottom':10, 'left':10, 'right': 10, 'g':10}
){


  // ----------------------------------------------->
  // ----- Function to calculate width of text ----->
  // ----------------------------------------------->

  function textWidth(text, fontSize=16, fontWeight=400, fontFamily=font.family) {

      // --- METHOD 1 --->
      /*container.append('text')
        .attr("x", -99999)
        .attr("y", -99999)
        .style("font-family", fontFamily)
        .style("font-size", fontSize + "px")
        .style("font-weight", fontWeight)
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





  // -------------------------------------------------------->
  // ----- Function to add TSPAN for each split-up text ----->
  // -------------------------------------------------------->

  function splitWrapTextSpan(text, width=100, fontSize=14, fontWeight=400, fontFamily=font.family, valign='bottom', dy_extra=0) {

    text.each(function() {

      var text = d3.select(this),
          lineNumber = 0,
          lineHeight = 1.1, // ems
          y = text.attr("y"),
          x = text.attr("x"),
          dy = parseFloat(text.attr("dy")),
          textSplit = splitWrapText(text.text(), width=width, fontSize=fontSize, fontWeight=fontWeight, fontFamily=fontFamily),
          tspan = text.text(null);

      var vshift = (valign == 'bottom')? 0: (valign == 'top')? (1.1): (1.1/2)

      textSplit.forEach(function(v, i, a){

          text.append('tspan')
              .attr("x", x)
              .attr("y", y)
              .attr("dy", `${((i * lineHeight) - ((a.length-1)*vshift) + (dy_extra))}em`)
              .text(v)
      });
    })

  }

  // <--------------------------------------------------------
  // <----- Function to add TSPAN for each split-up text -----
  // <--------------------------------------------------------





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
            'dy': (iTextSplit*1.1) + 'em',
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





  // ---------------------------------------->
  // ----- Function to add text to bars ----->
  // ---------------------------------------->

  function barText(d, fSize){

    d.each(function(v, i){

        var text = d3.select(this)
        var lineHeight = 1.1; // ems
        var y = text.attr("y");
        var x = text.attr("x");

        bar.text.forEach(function(v2, i2, a2){

          var text_val = ((v2['prefix'] != null)?v2['prefix']:'') + ((v2['var'] != null)?(d3.format(v2['format'])(v[v2['var']])): '') + ((v2['suffix'] != null)?v2['suffix']:'');

          text.append('tspan')
              .style("opacity", 0)
              .attr("class", function(d){ return 'tspan_' + i2})
              .attr("x", x)
              .attr("y", y)
              .attr("text-value", v[v2['var']])
              .attr('rect-width', function(d){
                return xScale(v['endRect']) - xScale(v['startRect'])
              })
              .attr("dy", `${(i2 * lineHeight) - ((1.1/2)*(bar.text.length))}em`)
              .text(function(){
                if(barmode == 'stack'){
                  if(textWidth(text_val, fontSize=fSize, fontWeight=yaxis.tick.weight, fontFamily=font.family) < ((xScale(v['endRect']) - xScale(v['startRect']))-6)){
                    return text_val
                  }
                  else{ return ''}
                }
                else{
                  return text_val
                }
              });

        });

    });

  }

  // <----------------------------------------
  // <----- Function to add text to bars -----
  // <----------------------------------------





  // ----------------------------------------------->
  // ----- Function to transition text in bars ----->
  // ----------------------------------------------->

  function barTransition(d){

    d.each(function(v, i){

        var text = d3.select(this)
        var lineHeight = 1.1; // ems
        var y = text.attr("y");
        var x = text.attr("x");

        bar.text.forEach(function(v2, i2, a2){

          //var text_val = ((v2['prefix'] != null)?v2['prefix']:'') + ((v2['var'] != null)?(d3.format(v2['format'])(v[v2['var']])): '') + ((v2['suffix'] != null)?v2['suffix']:'');

          text.select(".tspan_" + i2)
              .transition()
              .duration(800)
              .attr("text-value", v[v2['var']])
              .style("font-size", function(d){
                if(bar.height.var != null && Math.max(10, (height.bar*(d[bar.height.var]/maxBarHeightVal[domainScroll.indexOf(d['scroll'])][domainSwitcher.indexOf(d['switcher'])]))) < ((yaxis.tick.size*1.1)*bar.text.length)){
                  return (Math.max(10/bar.text.length, (height.bar*(d[bar.height.var]/maxBarHeightVal[domainScroll.indexOf(d['scroll'])][domainSwitcher.indexOf(d['switcher'])]))/bar.text.length) /1.1 ) + "px";
                }
                else{
                  return yaxis.tick.size + "px";
                }
              })
              //.attr('font-size', function(d){
              //  return xScale(v['endRect']) - xScale(v['startRect'])
              //})
              .attr('rect-width', function(d){
                return xScale(v['endRect']) - xScale(v['startRect'])
              })
              .attr("x", function(d){
                if(barmode == 'stack'){
                  return Math.min(xScale(v['startRect']), xScale(v['endRect'])) + ((Math.abs(xScale(v['startRect']) - xScale(v['endRect'])))/2)
                }
                else{
                  return xScale(v['endRect'])
                }
              })
              .textTween(function(d) {
                const fontInterpolate = d3.interpolate(
                  $(this).css('font-size').match(/\d+/)[0],
                  (bar.height.var != null && Math.max(10, (height.bar*(d[bar.height.var]/maxBarHeightVal[domainScroll.indexOf(d['scroll'])][domainSwitcher.indexOf(d['switcher'])]))) < (yaxis.tick.size*1.1))? (Math.max(10, (height.bar*(d[bar.height.var]/maxBarHeightVal[domainScroll.indexOf(d['scroll'])][domainSwitcher.indexOf(d['switcher'])]))) /1.1 ): yaxis.tick.size
                );
                const i = d3.interpolate($(this).attr('text-value'), v[v2['var']]);
                const j = d3.interpolate($(this).attr('rect-width'), Math.abs(xScale(v['endRect']) - xScale(v['startRect'])));
                return function(t) {

                  if(barmode == 'stack'){
                      if( textWidth(
                          text=parseFloat(i(t)).toFixed(1) + '%',
                          fontSize=fontInterpolate(t), //yaxis.tick.size,
                          fontWeight=yaxis.tick.weight,
                          fontFamily=font.family
                      ) < (j(t)-6) ){
                        return ((v2['prefix'] != null)?v2['prefix']:'') + ((v2['var'] != null)?(d3.format(v2['format'])(parseFloat(i(t)))): '') + ((v2['suffix'] != null)?v2['suffix']:'');
                      }
                      else { return ' '; }
                  }
                  else{
                    return ((v2['prefix'] != null)?v2['prefix']:'') + ((v2['var'] != null)?(d3.format(v2['format'])(parseFloat(i(t)))): '') + ((v2['suffix'] != null)?v2['suffix']:'');
                  }

                };
              })

        });

    });

  }

  // <-----------------------------------------------
  // <----- Function to transition text in bars -----
  // <-----------------------------------------------





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
              return `translate(${(canvas_width*1.5)}, ${height.scrollLabel})`
            }
            else{
              return `translate(${(-canvas_width*1.5)}, ${height.scrollLabel})`
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
              return `translate(${(-canvas_width*1.5)}, ${height.scrollLabel})`
            }
            else{
              return `translate(${(canvas_width*1.5)}, ${height.scrollLabel})`
            }
          })




    // --- Move individual charts --->
    svg.select('.g_scroll_' + nextScrollIndex)
      .transition()
      .duration(0)
          .attr('x', function(){
            (method == 'up')? canvas_width: -canvas_width
          })
          .attr('transform', function(){
            if(method == 'up'){
              return `translate(${((canvas_width*1) + margin.left)}, ${margin.top + height.title + height.scroll + height.switcher + height.legend})`
            }
            else{
              return `translate(${((-canvas_width*1) + margin.left)}, ${margin.top + height.title + height.scroll + height.switcher + height.legend})`
            }
          })
      .transition()
          .duration(500)
          .attr('opacity', 1)
          .attr('x', canvas_width*0)
          .attr('transform', function(){
              return `translate(${(margin.left)}, ${margin.top + height.title + height.scroll + height.switcher + height.legend})`
          })


    svg.select('.g_scroll_' + scrollIndex)
      .transition()
      .duration(500)
          .attr('opacity', 0)
          .attr('x', function(){
            (method == 'up')? -canvas_width: canvas_width
          })
          .attr('transform', function(d, i){
            if(method == 'up'){
              return `translate(${(-canvas_width + margin.left)}, ${margin.top + height.title + height.scroll + height.switcher + height.legend})`
            }
            else{
              return `translate(${(canvas_width + margin.left)}, ${margin.top + height.title + height.scroll + height.switcher + height.legend})`
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





  // -------------------------------------------------------->
  // ----- Function to decide if color is light or dark ----->
  // -------------------------------------------------------->

  function lightOrDark(color) {

    // Variables for red, green, blue values
    var r, g, b, hsp;

    // Check the format of the color, HEX or RGB?
    if (color.match(/^rgb/)) {

        // If RGB --> store the red, green, blue values in separate variables
        color = color.match(/^rgba?\((\d+),\s*(\d+),\s*(\d+)(?:,\s*(\d+(?:\.\d+)?))?\)$/);

        r = color[1];
        g = color[2];
        b = color[3];
    }
    else {

        // If hex --> Convert it to RGB: http://gist.github.com/983661
        color = +("0x" + color.slice(1).replace(
        color.length < 5 && /./g, '$&$&'));

        r = color >> 16;
        g = color >> 8 & 255;
        b = color & 255;
    }

    // HSP (Highly Sensitive Poo) equation from http://alienryderflex.com/hsp.html
    hsp = Math.sqrt(
    0.299 * (r * r) +
    0.587 * (g * g) +
    0.114 * (b * b)
    );

    // Using the HSP value, determine whether the color is light or dark
    // if (hsp>127.5) {
    if (hsp>128.5) {

        return 'light';
    }
    else {

        return 'dark';
    }
  }

  // <--------------------------------------------------------
  // <----- Function to decide if color is light or dark -----
  // <--------------------------------------------------------





  // ------------------------------------------->
  // ---- Function to change Bars and Text ----->
  // ------------------------------------------->

  function changeBars(iSwitch){

      dataPlot.forEach(function(vData, iData){

        vData[iSwitch].forEach(function(vFacet, iFacet){


            svg.selectAll('.scroll_' + iData)
              .filter('.facet_' + iFacet)
              .data(vFacet)
                .transition()
                .attr("class", function(d, i){
                  return 'scroll_' + iData +
                  ' switcher_' + iSwitch +
                  ' group_' + domainGroup.map(d => d['group']).indexOf(d['group']) +
                  ' obs_' + iData + '_0_' + domainGroup.map(d => d['group']).indexOf(d['group']) + '_' + i +
                  ' level level_' + domainY.indexOf(d['y']) +
                  ' facet_' + iFacet
                })
                //.select('.facet_' + iFacet)
                .attr('startRect', d => xScale(d['startRect']))
                .attr('endRect', d => xScale(d['endRect']))
                .attr('widthRect', d => xScale(d['endRect']) - xScale(d['startRect']))
                .attr('color-value', d => d[clr_var])
                .attr('group-value', function(d){
                  if(group.var != null){ return d['group'] }
                  else{ return '' }
                })
                .attr('x-value', d => d[x.var])
                .attr('y-value', function(d){
                  if(barmode == 'group'){ return yScale[iFacet](d['y']) + (yScale[iFacet].bandwidth()*(domainGroup.map(d => d['group']).indexOf(d['group'])/domainGroup.length)) }
                  else{ return yScale[iFacet](d['y']) }
                });


            svg.select('.g_scroll_' + iData)
              .select('.facet_' + iFacet)
              .selectAll('.bar_rect')
              .data(vFacet)
              .transition()
                .duration(800)
                .attr("x", function(d){ return xScale(d['startRect']) })
                .attr("y", function(d, i){
                  if(barmode == 'group'){
                    return (yScale[iFacet](d['y']) + (yScale[iFacet].bandwidth()/2) - (height.bar/2)) + (barShiftScale(domainGroup.map(d => d['group']).indexOf(d['group'])))
                  }
                  else{
                    if(bar.height.var != null){
                      return yScale[iFacet](d['y']) + (yScale[iFacet].bandwidth()/2) - (Math.max(10, height.bar*(d[bar.height.var]/maxBarHeightVal[domainScroll.indexOf(d['scroll'])][domainSwitcher.indexOf(d['switcher'])]))/2)
                    }
                    else{
                      return yScale[iFacet](d['y']) + (yScale[iFacet].bandwidth()/2) - (height.bar/2)
                    }
                  }
                })
                .attr("width", function(d){ return Math.abs(xScale(d['endRect']) - xScale(d['startRect'])) })
                .attr("height", function(d){
                  if(bar.height.var != null){
                    return Math.max(10, height.bar*(d[bar.height.var]/maxBarHeightVal[domainScroll.indexOf(d['scroll'])][domainSwitcher.indexOf(d['switcher'])]))
                  }
                  else{
                    return height.bar
                  }
                });




            svg.select('.g_scroll_' + iData).select('.facet_' + iFacet)
              .selectAll('.bar_text')
              .data(vFacet)
              .each(d => d)
              .call(barTransition);
            })

      });

  };

  // <-------------------------------------------
  // <---- Function to change Bars and Text -----
  // <-------------------------------------------








  // ---------------->
  // ----- DATA ----->
  // ---------------->

  //var domainFacet = Array.from(new Set(data.map(d => d[facet.var].toString())));
  //if(facet.order == 'alphabetical'){ domainFacet.sort(); }

  var domainFacet = []
  Array.from(new Set(data.map(d => d[facet.var].toString()))).forEach(function(v, i){
    var facetY = Array.from(new Set(data.filter(d => d[facet.var] == v).map(d => d[y.var].toString())));
    if(y.order == 'alphabetical'){ facetY.sort(); }

    domainFacet[i] = {'facet': v, 'y': facetY}
  })

  //var domainFacet = (facet.var != null)? Array.from(new Set(data.map(d => d[facet.var]))): [null];
  //console.log('domainFacet', domainFacet);


  var domainY = Array.from(new Set(data.map(d => d[y.var].toString())));
  if(y.order == 'alphabetical'){ domainY.sort(); }
  //console.log('domainY', domainY);


  // Get color of groups
  var domainGroup = [];
  if(group.var != null){
    Array.from(new Set(data.map(d => d[group.var]))).forEach(function(v, i){
      domainGroup.push({
        'group': v,
        'color': data.filter(d => d[group.var] == v).map(d => d[clr_var])[0]
      })
    })

  }
  else{
    domainGroup = [{'group':null, 'color':null}];
  }
  if(group.var != null && group.order == 'alphabetical'){ domainGroup.sort(); }
  //console.log('### domainGroup', domainGroup);


  var domainSwitcher = (switcher.var != null)? Array.from(new Set(data.map(d => d[switcher.var]))): [null];
  if(switcher.var != null && switcher.order == 'alphabetical'){ domainSwitcher.sort(); }
  //console.log('### domainSwitcher', domainSwitcher);


  var domainScroll = (scroll.var != null)? Array.from(new Set(data.map(d => d[scroll.var]))): [null];
  if(scroll.var != null && scroll.order == 'alphabetical'){ domainScroll.sort(); }
  //console.log('### domainScroll', domainScroll);


  var maxBarHeightVal = [];
  if(bar.height.var != null){

    domainScroll.forEach(function(vScroll, iScroll){
      maxBarHeightVal[iScroll] = []

      domainSwitcher.forEach(function(vSwitcher, iSwitcher){
          //maxBarHeightVal[iScroll][iSwitcher] = [];

          maxBarHeightVal[iScroll][iSwitcher] =  d3.max(data.filter(d => ((scroll.var != null)? d[scroll.var] == vScroll: true) && ((switcher.var != null)? d[switcher.var] == vSwitcher: true)).map(d => d[bar.height.var]))
      });
    });
  }
  //console.log('maxBarHeightVal', maxBarHeightVal)


  // Create data that has all combinations of all values
  var minXvalue = (xaxis.range[0] != null)? xaxis.range[0]: d3.min(data, d => d[x.var]);
  var dataPlot = [];

  domainScroll.forEach(function(vScroll, iScroll){
    dataPlot[iScroll] = []

    domainSwitcher.forEach(function(vSwitcher, iSwitcher){
      dataPlot[iScroll][iSwitcher] = [];

      domainFacet.forEach(function(vFacet, iFacet){
        dataPlot[iScroll][iSwitcher][iFacet] = [];

          vFacet['y'].forEach(function(vY, iY){

            var startRect = minXvalue;

            domainGroup.forEach(function(vGroup, iGroup){
                //console.log('vGroup', vGroup)

                var dataObs = data.filter(d => ((scroll.var != null)? d[scroll.var] == vScroll: true) && ((switcher.var != null)? d[switcher.var] == vSwitcher: true) && ((group.var != null)? d[group.var] == vGroup['group']: true) && d[y.var] == vY)[0]

                var newObs = {
                  'scroll': vScroll,
                  'switcher': vSwitcher,
                  'facet': (facet.var != null && dataObs)? dataObs[facet.var]: null,
                  'group': (group.var != null)? vGroup['group']: null,
                  'clr': (dataObs)? dataObs[clr_var]:'white', //vGroup['color'], //dataObs[clr_var],
                  'y': vY,
                  'x': (dataObs)? dataObs[x.var]:0,
                  'startRect': startRect,
                  //'endRect': (barmode=='stack')?(startRect + ((dataObs)? dataObs[x.var]:0)): ((dataObs)? dataObs[x.var]:0)
                  'endRect': (startRect + ((dataObs)? dataObs[x.var]:0))
                }


                if(barmode == 'stack'){
                  startRect += ((dataObs)? dataObs[x.var]:0)
                }

                if(bar.text != null){
                  bar.text.forEach((v, i) => {
                      newObs[v['var']] = (dataObs)?dataObs[v['var']]: 0
                  });
                }

                if(tooltip_text != null){
                  tooltip_text.forEach((v, i) => {
                      v['text'].forEach((v2, i2) => {
                        newObs[v2['var']] = (dataObs)?dataObs[v2['var']]: null
                      })
                  });
                }

                if(bar.height.var != null){
                  newObs[bar.height.var] = (dataObs)?dataObs[bar.height.var]: 0
                }

                dataPlot[iScroll][iSwitcher][iFacet].push(newObs);
            })
          })
        })
    })
  })
  //console.log('### dataPlot', dataPlot);

  // <----------------
  // <----- DATA -----
  // <----------------










  // ------------------------>
  // ----- Graph Sizing ----->
  // ------------------------>

  var canvas_width = 960;

  var height = {
    'bar': (bar.text != null)? ( ((((yaxis.tick.size*1.1)*bar.text.length)+6)*100)/90 + bar.extra_height ) : ( (((yaxis.tick.size*1.1)+6)*100)/90 + bar.extra_height )
  };



  // Title Height
  height.title = 0;
  if(title.value != null){
    height.title = margin.g + (title.size*1.1)*splitWrapText(title.value, (canvas_width - margin.left - margin.right), fontSize=title.size, fontWeight=title.weight, fontFamily=font.family).length;
  }



  // Scroll Height
  height.scroll = 0;
  height.scrollLabel = 0;
  if(scroll.var != null ){

    domainScroll.forEach(function(vScroll, iScroll){
      var numScrollLines = splitWrapText(vScroll, (canvas_width - margin.left - margin.right - (scroll.size*2)), fontSize=scroll.size, fontWeight=scroll.weight, fontFamily=font.family).length;

      height.scroll = (((scroll.size*1.1)*numScrollLines) > height.scroll)? ((scroll.size*1.1)*numScrollLines): height.scroll;
    })

    if(scroll.label.value != null){
      var numScrollLabelLines = splitWrapText(scroll.label.value, (canvas_width - margin.left - margin.right), fontSize=scroll.label.size, fontWeight=scroll.label.weight, fontFamily=font.family).length;
      height.scrollLabel = numScrollLabelLines*(scroll.label.size*1.1) + 5
      height.scroll += height.scrollLabel
    }

    height.scroll += margin.g;
  }



  // Switcher Height
  height.switcher = 0;
  height.switcherLabel = 0;
  if(switcher.var != null ){
    var switcherText = splitWrapTextElement(domainSwitcher, width=canvas_width-(margin.left+margin.right), padding=16, extra_width=0, fSize=switcher.size, fWeight=switcher.weight, fFamily=font.family);

    var maxY = d3.max(switcherText.map(d => d['y']));
    var maxLine = d3.max(switcherText.map(d => d['line']));
    var maxRowInLastLine = 0;

    switcherText.filter(d => d['line'] == maxLine).map(d => d['text']).forEach(function(v, i){
      if(v.length > maxRowInLastLine){ maxRowInLastLine = v.length}
    });

    if(switcher.label.value != null){
      var numSwitchLabelLines = splitWrapText(switcher.label.value, (canvas_width - margin.left - margin.right), fontSize=switcher.label.size, fontWeight=switcher.label.weight, fontFamily=font.family).length;
      height.switcherLabel = numSwitchLabelLines*(switcher.label.size*1.1) + 5
      //height.switcher += height.switcherLabel
    }

    height.switcher = margin.g + maxY + (maxRowInLastLine*(switcher.size*1.1)) + 10 + height.switcherLabel
  }



  // Legend Height
  height.legend = 0;
  height.legendLabel = 0;
  if(group.var != null ){
    var legendText = splitWrapTextElement(domainGroup.map(d => d['group']), width=canvas_width-(margin.left+margin.right), padding=10, extra_width=14+5, fSize=group.size, fWeight=group.weight, fFamily=font.family);

    // Get colors
    legendText.forEach(function(v, i){
      v['color'] = domainGroup[i]['color']
    });

    if(group.label.value != null){
      var numLegendLabelLines = splitWrapText(group.label.value, (canvas_width - margin.left - margin.right), fontSize=group.label.size, fontWeight=group.label.weight, fontFamily=font.family).length;
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



  //height.yaxis = (barmode=='group')? ((height.bar*Math.max(domainGroup.length, maxNumTickLines))*domainY.length): (height.bar*domainY.length);
  //height.yaxis0 = (barmode=='group')? ((height.bar*domainGroup.length)*domainY.length): (height.bar*domainY.length);
  height.yaxis0 = (barmode=='group')?  ((((height.bar*domainGroup.length)*100)/90)*domainY.length): (((height.bar*100)/90)*domainY.length);
  margin.yaxislabel = (yaxis.label.value != null)? (yaxis.label.size*1.1)*splitWrapText(yaxis.label.value, height.yaxis0, fontSize=yaxis.label.size, fontWeight=yaxis.label.weight, fontFamily=font.family).length + (10) : 0;


  margin.yaxis = 0;
  var maxNumTickLines = 0;
  if(yaxis.show){
    domainY.forEach(function(v, i){
      splitWrapText(v, (canvas_width*0.4) - (margin.left + margin.yaxislabel), yaxis.tick.size, yaxis.tick.weight, font.family).forEach(function(vSplit, iSplit, aSplit){

          maxNumTickLines = (aSplit.length > maxNumTickLines)?aSplit.length : maxNumTickLines;

          if((textWidth(vSplit, yaxis.tick.size, yaxis.tick.weight, font.family)+20) > margin.yaxis){
          margin.yaxis = textWidth(vSplit, yaxis.tick.size, yaxis.tick.weight, font.family)+20
        }
      })
    })
  }


  // Re-calculate y-axis height
  if(barmode=='group'){
    if((height.bar*domainGroup.length) < (maxNumTickLines*(yaxis.tick.size*1.1)+6)){
      //height.yaxis = (maxNumTickLines*(yaxis.tick.size*1.1)+6)*domainY.length;
      height.yaxis = (((maxNumTickLines*(yaxis.tick.size*1.1)+6)*100)/90)*domainY.length;
    }
    else{
      //height.yaxis = height.bar*domainGroup.length*domainY.length;
      height.yaxis = ((((height.bar*domainGroup.length)*100)/90)*domainY.length)
    }
  }
  else{
    if((maxNumTickLines*(yaxis.tick.size*1.1)) > (((height.bar)*100)/90)){
      //height.yaxis = (maxNumTickLines*(yaxis.tick.size*1.1)+6)*domainY.length;
      height.yaxis = ((maxNumTickLines*(yaxis.tick.size*1.1))+6)*domainY.length;
    }
    else{
      //height.yaxis = height.bar*domainY.length;
      height.yaxis = (((height.bar*100)/90)*domainY.length)
    }
  }

  height.xaxis = ((xaxis.show)?(xaxis.tick.size*1.1) + 15: 0) + ( (xaxis.label.value != null)? (xaxis.label.size*1.1)*splitWrapText(xaxis.label.value, (canvas_width - (margin.left + margin.yaxislabel + margin.yaxis + margin.right)), fontSize=xaxis.label.size, fontWeight=xaxis.label.weight, fontFamily=font.family).length : 0 )



  // Facet Height
  var facet_ypos = [];
  height.facetLabel = [];
  height.facet = 0;
  if(facet.var != null ){

    var facetPos = 0;

    domainFacet.forEach(function(vFacet, iFacet){
      var numFacetLabelLines = splitWrapText(vFacet['facet'], (canvas_width - margin.left - margin.right), fontSize=facet.size, fontWeight=facet.weight, fontFamily=font.family).length;
      height.facetLabel[iFacet] = numFacetLabelLines*(facet.size*1.1);

      facet_ypos[iFacet] = facetPos + height.facetLabel[iFacet];

      facetPos += height.facetLabel[iFacet] + (height.yaxis*(vFacet['y'].length/domainY.length));
    })


    height.facet += d3.sum(height.facetLabel);
    //console.log('height.facetLabel', height.facetLabel)
    //console.log('height.facet', height.facet)
    //console.log('facet_ypos', facet_ypos)
  }


  var canvas_height = margin.top + height.title + height.scroll + height.switcher + height.legend + yaxis.offset.top + height.yaxis + height.facet + yaxis.offset.bottom + height.xaxis + margin.bottom;


  margin.bar_text = 0;
  if(barmode == 'group'){

    dataPlot.forEach(function(v, i){

      v.forEach(function(v2, i2){
        v2.forEach(function(v3, i3){

          bar.text.forEach(function(v4, i4, a4){
            var text_val = ((v4['prefix'] != null)?v4['prefix']:'') + ((v4['var'] != null)?(d3.format(v4['format'])(v3[v4['var']])): '') + ((v4['suffix'] != null)?v4['suffix']:'');

            margin.bar_text = ( (textWidth(text_val, yaxis.tick.size, yaxis.tick.weight)+5) > margin.bar_text)? (textWidth(text_val, yaxis.tick.size, yaxis.tick.weight)+5): margin.bar_text;
          })

        })

      })

    })

  }



  // <------------------------
  // <----- Graph Sizing -----
  // <------------------------











  // ----- Change height of parent DIV ----->
  /*d3.select(html_id)
    .style("height", (canvas_height + 10) + 'px') ;*/

  // ----- Create SVG element ----->
  var svg = d3.select(html_id)
      .append("div")
      .classed("svg-container", true)
      .append("svg")
      .attr("preserveAspectRatio", "xMinYMin meet")
      .attr("viewBox", "0 0 " + canvas_width + " " + canvas_height)
      .classed("svg-content", true)
      .append('g');


  var svg_g = svg.append('g')
    .on('mouseover', (event, v) => {
          g_skills.transition()
            .duration(500)
            .attr('transform', `translate(${canvas_width}, ${0})`);
    })

      /*d3.select(html_id)
      .append("svg")
      .attr("width", canvas_width)
      .attr("height", canvas_height)
      //.attr("viewBox", [-canvas_width/2, -canvas_height/2, canvas_width, canvas_height])
      //.attr("style", "max-width: 100%; height: auto; height: intrinsic;");*/





  // ----------------->
  // ----- TITLE ----->
  // ----------------->

  // Group
  var g_title = svg_g.append("g")
    .attr("class", "g_title")
    .attr('transform', `translate(${margin.left}, ${margin.top})`);


  //  Title Text
  if(title.value != null){
      g_title.selectAll('title_text')
          .data(splitWrapText(title.value, (canvas_width - margin.left - margin.right), fontSize=title.size, fontWeight=title.weight, fontFamily=font.family))
          .enter()
          .append("text")
            .style("font-family", font.family)
            .style("font-size", title.size +  "px")
            .style('font-weight', title.weight)
            .style("text-anchor", "middle")
            .style("dominant-baseline", "hanging")
            .attr("class", "title_text")
            .attr('x', margin.left + ((canvas_width - margin.left - margin.right)/2))
            .attr("dy", function(d, i){ return i*1.1 + 'em'})
            .text(d => d);

      if(title.line){
          g_title.append('path')
            .attr('d', 'M' + 0 + ',' + (height.title - (margin.g/2)) + 'L' + (canvas_width - (margin.left + margin.right)) + ',' + (height.title - (margin.g/2)))
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
  var g_scroll = svg_g.append("g")
    .attr("class", "g_scroll")
    .attr('transform', `translate(${margin.left}, ${margin.top + height.title})`);


  if(scroll.var != null){

    // Scroll Label
    if(scroll.label.value != null){
        g_scroll.selectAll('scroll_title')
            .data(splitWrapText(scroll.label.value, (canvas_width - margin.left - margin.right), fontSize=scroll.label.size, fontWeight=scroll.label.weight, fontFamily=font.family))
            .enter()
            .append("text")
              .attr("class", "scroll_title")
              .style("font-family", font.family)
              .style("font-size", scroll.label.size +  "px")
              .style('font-weight', scroll.label.weight)
              .style("text-anchor", "middle")
              .style("dominant-baseline", "hanging")
              .attr('x', (canvas_width - margin.left - margin.right)/2)
              .attr("dy", function(d, i){ return i*1.1 + 'em'})
              .text(d => d);
      }



      var maxScrollWidth = 0;

      domainScroll.forEach(function(vScroll, iScroll){

          var scrollData = splitWrapText(vScroll, (canvas_width - margin.left - margin.right - (scroll.size*2)), fontSize=scroll.size, fontWeight=scroll.weight, fontFamily=font.family)

          g_scroll.selectAll('scroll_text')
              .data(scrollData)
              .enter()
              .append("text")
                .attr("class", "scroll_text_" + iScroll)
                .attr('opacity', function(){ return 1 - Math.min(iScroll, 1) })
                .style("font-family", font.family)
                .style("font-size", scroll.size +  "px")
                .style('font-weight', scroll.weight)
                .style("text-anchor", "middle")
                .style("dominant-baseline", "hanging")
                .attr('x', (canvas_width - margin.left - margin.right)/2)
                .attr('transform', `translate(${(Math.min(iScroll, 1)*canvas_width)}, ${height.scrollLabel})`)
                .attr("dy", function(d, i){ return i*1.1 + 'em'})
                .text(d => d);


          scrollData.forEach(function(vScroll2, iScroll2){
            maxScrollWidth = (textWidth(vScroll2, fontSize=scroll.size, fontWeight=scroll.weight, fontFamily=font.family) > maxScrollWidth)? textWidth(vScroll2, fontSize=scroll.size, fontWeight=scroll.weight, fontFamily=font.family): maxScrollWidth;
          })
      });


      var scrollIndex = 0;

      g_scroll.append('path')
            .attr("class", "scroll_right")
            .attr('d', 'M' + (canvas_width - (margin.left + margin.right))/2 + ',' + (height.scrollLabel) + 'L' + (canvas_width - (margin.left + margin.right))/2 + ',' + ((height.scrollLabel) + (height.scroll-margin.g-height.scrollLabel)) + 'L' + (((canvas_width - (margin.left + margin.right))/2)-scroll.size) + ',' + ((height.scrollLabel) + (height.scroll-margin.g-height.scrollLabel)/2) + 'L' + ((canvas_width - (margin.left + margin.right))/2) + ',' + (height.scrollLabel))
            .attr("stroke", "#d3d2d2")
            .attr("fill", "#d3d2d2")
            .attr('transform', `translate(${-((maxScrollWidth/2) + 20)}, ${0})`)
            .on('click', function(event){
              scrollChart('down')
            })
            .on("mouseover", function(d) {
                d3.select(this).style("cursor", "pointer");
            });


      g_scroll.append('path')
            .attr("class", "scroll_right")
            .attr('d', 'M' + (canvas_width - (margin.left + margin.right))/2 + ',' + (height.scrollLabel) + 'L' + (canvas_width - (margin.left + margin.right))/2 + ',' + ((height.scrollLabel) + (height.scroll-margin.g-height.scrollLabel)) + 'L' + (((canvas_width - (margin.left + margin.right))/2)+scroll.size) + ',' + ((height.scrollLabel) + (height.scroll-margin.g-height.scrollLabel)/2) + 'L' + ((canvas_width - (margin.left + margin.right))/2) + ',' + (height.scrollLabel))
            .attr("stroke", "#d3d2d2")
            .attr("fill", "#d3d2d2")
            .attr('transform', `translate(${((maxScrollWidth/2) + 20)}, ${0})`)
            .on('click', function(event){
              scrollChart('up')
            })
            .on("mouseover", function(d) {
                d3.select(this).style("cursor", "pointer");
            });


      if(scroll.line){
          g_scroll.append('path')
            .attr('d', 'M' + 0 + ',' + (height.scroll - (margin.g/2)) + 'L' + (canvas_width - (margin.left + margin.right)) + ',' + (height.scroll - (margin.g/2)))
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
  var g_switcher = svg_g.append("g")
    .attr("class", "g_switcher")
    .attr('transform', `translate(${canvas_width/2}, ${margin.top + height.title + height.scroll})`);

  if(switcher.var != null){

    // Switcher Label
    if(switcher.label.value != null){
        g_switcher.selectAll('switch_title')
            .data(splitWrapText(switcher.label.value, (canvas_width - margin.left - margin.right), fontSize=switcher.label.size, fontWeight=switcher.label.weight, fontFamily=font.family))
            .enter()
            .append("text")
              .attr("class", "switcher_title")
              .style("font-family", font.family)
              .style("font-size", switcher.label.size +  "px")
              .style('font-weight', switcher.label.weight)
              .style("text-anchor", "middle")
              .style("dominant-baseline", "hanging")
              .attr('x', 0)
              .attr("dy", function(d, i){ return i*1.1 + 'em'})
              .text(d => d);
      }



    var switcherGroup = g_switcher.selectAll('.switcher')
        .data(switcherText)
        .enter()
        .append("g")
          .attr("class", function(d, i){ return "switcher switcher_" + i})
          .attr('transform', function(d){ return `translate(${d['x']}, ${(d['y'] + height.switcherLabel)})` })
          .attr("opacity", function(d, i){
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
      .attr("class", function(d, i){ return "switcher_" + i})
      .attr('width-value', d => d['width-value'])
      //.attr('x', d => 0 - (d['width-value']/2))
      //.attr('x', -5)
      .attr('x', 5)
      .attr('y', -3)
      .attr('width', d => d['width-value']-8)
      .attr('height', d => (d['text'].length*(switcher.size*1.1)) + 6)
      .attr('fill', '#d3d2d2');


    switcherGroup.append("text")
      .attr("class", function(d, i){ return "switcher_" + i})
      .style("font-family", font.family)
      .style("font-size", switcher.size +  "px")
      .style('font-weight', switcher.weight)
      //.style("text-anchor", "start")
      .style("text-anchor", "middle")
      .style("dominant-baseline", "hanging")
      .attr('width-value', d => d['width-value'])
      .attr('x', 0)
      //.attr('x', d => d['width-value']/2)
      .each(function(d, i){
        d3.select(this).selectAll('.switcher_text_' + i)
          .data(d['text'])
          .enter()
          .append('tspan')
          //.attr('x', d => (d['max-width-value'] - d['this-width-value'])/2) // Centre-align horizontally
          //.attr('x', 0) // Centre-align horizontally
          .attr('x', d => d['max-width-value']/2) // Centre-align horizontally
          .attr('dy', d => d['dy'])
          .text( d => d['value'])
      });


    if(switcher.line){
        g_switcher.append('path')
          .attr('d', 'M' + 0 + ',' + (height.switcher - (margin.g/2)) + 'L' + (canvas_width - (margin.left+margin.right)) + ',' + (height.switcher - (margin.g/2)))
          .attr('stroke', '#d3d2d2')
          .attr('stroke-width', '2')
          .attr('transform', function(d){ return `translate(${(-(canvas_width/2)+margin.left)}, ${0})` })

    }
  }

  // <--------------------
  // <----- SWITCHER -----
  // <--------------------










  // ------------------>
  // ----- LEGEND ----->
  // ------------------>

  // Group
  var g_legend = svg_g.append("g")
    .attr("class", "g_legend")
    .attr('transform', `translate(${canvas_width/2}, ${margin.top + height.title + height.scroll + height.switcher})`);


  if(group.var != null){
      // Legend Label
      if(group.label.value != null){
          g_legend.selectAll('legend_title')
              .data(splitWrapText(group.label.value, (canvas_width - margin.left - margin.right), fontSize=group.label.size, fontWeight=group.label.weight, fontFamily=font.family))
              .enter()
              .append("text")
                .attr("class", "legend_title")
                .style("font-family", font.family)
                .style("font-size", group.label.size +  "px")
                .style('font-weight', group.label.weight)
                .style("text-anchor", "middle")
                .style("dominant-baseline", "hanging")
                .attr('x', 0)
                .attr("dy", function(d, i){ return i*1.1 + 'em'})
                .text(d => d);
      }

      var legend = g_legend.selectAll('.legend')
          .data(legendText)
          .enter()
          .append("g")
            .attr("class", function(d, i){ return "legend_" + i})
            //.attr('transform', function(d){ return `translate(${d['x']}, ${d['y']})` })
            .attr('transform', function(d){ return `translate(${d['x']}, ${(d['y'] + height.legendLabel)})` })
            .attr("opacity", 1.0)
            .on('click', (event, v) => {

                  if(+event.currentTarget.getAttribute('opacity') == 1){
                      svg.select('.' + event.currentTarget.getAttribute('class')).attr('opacity', 0.2);
                      svg.selectAll('.group_' + event.currentTarget.getAttribute('class').split('_')[1]).transition().duration(200).style('opacity', 0);
                  }
                  else{
                      svg.select('.' + event.currentTarget.getAttribute('class')).attr('opacity', 1.0);
                      svg.selectAll('.group_' + event.currentTarget.getAttribute('class').split('_')[1]).transition().duration(200).style('opacity', 1);
                  }

            })
            .on("mouseover", function(d) {
                d3.select(this).style("cursor", "pointer");
            });


      legend.append('rect')
        .attr("class", function(d, i){ return "legend_" + i})
        .attr('x', 0)
        .attr('width', group.size)
        .attr('height', group.size)
        .attr('fill', d => d['color']);

      legend.append("text")
        .attr("class", function(d, i){ return "legend_" + i})
        .style("font-family", font.family)
        .style("font-size", group.size +  "px")
        .style('font-weight', group.weight)
        .style("text-anchor", "start")
        .style("dominant-baseline", "hanging")
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








  // ---------------->
  // ----- AXES ----->
  // ---------------->

  // --- Y-Axis --->

  // Scale
  var yScale = [], yAxisChart = [];
  domainFacet.forEach(function(v, i){

    yScale[i] = d3.scaleBand()
      .domain(v['y'])
      .range([
        //yaxis.offset.top,
        //yaxis.offset.top + (height.yaxis*(v['y'].length/domainY.length))
        0,
        (height.yaxis*(v['y'].length/domainY.length))
      ])
      .padding([0.10]);

    // Axis
    yAxisChart[i] = d3.axisLeft(yScale[i]);

  })

  /*var yScale = d3.scaleBand()
    .domain(domainY)
    .range([
      yaxis.offset.top,
      yaxis.offset.top + height.yaxis
    ])
    .padding([0.10]);

  // Axis
  var yAxisChart = d3.axisLeft(yScale);*/

  // <--- Y-Axis ---





  // --- X-Axis --->

  // Scale
  var minXvalue = Infinity;
  var maxXvalue = -Infinity;
  dataPlot.forEach(function(v1, i1){
    v1.forEach(function(v2, i2){
      v2.forEach(function(v3, i3){
        minXvalue = (v3['startRect'] < minXvalue)? v3['startRect']: minXvalue;
        maxXvalue = (v3['endRect'] > maxXvalue)? v3['endRect']: maxXvalue;
      })
    })
  });

  var xScale = d3.scaleLinear()
    .domain([
      (xaxis.range[0] != null)? xaxis.range[0]: minXvalue,
      (xaxis.range[1] != null)? xaxis.range[1]: maxXvalue
    ])
    .range([
      margin.yaxislabel + margin.yaxis + xaxis.offset.left,
      canvas_width - (margin.left + xaxis.offset.right + margin.right + margin.bar_text)
    ]);


  // Axis
  var xAxisChart = d3.axisBottom()
  .scale(xScale)
  .tickFormat((d) => (xaxis.suffix != null)? (d + xaxis.suffix): d);

  if(xaxis.num_ticks != null){
    xAxisChart.ticks(xaxis.num_ticks)
  }
  if(xaxis.show_grid){
    xAxisChart.tickSize(-(height.yaxis + yaxis.offset.bottom));
  }

  // <--- X-Axis ---





  // --- Scale for shifting bars up/down Y-Axis bandwidth --->

  var barShiftScale = d3.scaleLinear()
    .domain([
      0,
      domainGroup.length-1
    ])
    .range([
      -((domainGroup.length-1)*(height.bar/2)),
      (domainGroup.length-1)*(height.bar/2)
    ]);

  // <--- Scale for shifting bars up/down Y-Axis bandwidth ---

  // <----------------
  // <----- AXES -----
  // <----------------


  //console.log('#####', html_id)
  //console.log('### yScale Range:', yScale.range()[1] - yScale.range()[0])
  //console.log('### Bandwidth x Length:', yScale.bandwidth() * domainY.length)
  //console.log('# y Bandwidth:', yScale.bandwidth())
  //console.log('# y Length:', domainY.length)
  //console.log('# Bar Height:', height.bar)














  // --------------------->
  // ----- BAR CHART ----->
  // --------------------->



  // ----- Group ----->
  var g_chart = svg_g.selectAll('.g_chart')
    .data(domainScroll)
    .enter()
    .append("g")
    .attr("class", function(d, i){ return "g_chart g_scroll_" + i})
    .attr('opacity', function(d, i){ return 1 - Math.min(i, 1) })
    .attr('x', function(d, i){
      return canvas_width*i
    })
    .attr('transform', function(d, i){
      return `translate(${((canvas_width*Math.min(1, i)) + margin.left)}, ${margin.top + height.title + height.scroll + height.switcher + height.legend})`
    });






  // ----- Add Y-Axis Label to plot ----->
  /*if(yaxis.label.value != null){
      g_chart.append("text")
        .style("font-family", font.family)
        .style("font-size", yaxis.label.size + "px")
        .style('font-weight', yaxis.label.weight)
        .style("text-anchor", "middle")
        .style("dominant-baseline", "hanging")
        .attr('x', -(yScale.range()[0] + ((yScale.range()[1] - yScale.range()[0])*0.5)) ) // Moves vertically (due to rotation)
        .attr("y", 0) // Moves horizontally (due to rotation)
        .attr("transform", "rotate(-90)")
        .text(yaxis.label.value)
        .call(splitWrapTextSpan, height.yaxis0, yaxis.label.size, yaxis.label.weight, font.family, valign='bottom', dy_extra=0);
  }


  // ----- Add Y-Axis to plot ----->
  if(yaxis.show){
    var y_axis_chart = g_chart.append("g")
        .attr("class", "y_axis")
        .style("font-size", yaxis.tick.size + "px")
        .attr("transform", "translate(" + (margin.yaxislabel+margin.yaxis) + "," + 0 + ")")
        .call(yAxisChart);


    y_axis_chart.selectAll(".tick text")
        .attr("y", '0.0')
        .call(splitWrapTextSpan, ((canvas_width*0.4) - (margin.left + margin.yaxislabel)), yaxis.tick.size, yaxis.tick.weight, font.family, valign='center', dy_extra=0.32);

    // Remove Axis Line
    if(!yaxis.show_line){
      y_axis_chart.select(".domain").remove();
    }

    // Remove Axis Ticks
    if(!yaxis.show_ticks){
      y_axis_chart.selectAll(".tick").selectAll("line").remove();
    }


    // Show model text in separate div when click on y-axis elements
    y_axis_chart.selectAll(".tick").selectAll("text")
    .on("click",function(d, i) {

      text_sim_decisions(
        data = data_sim_model_text.filter(d => d['simname'] == simSelector.value && d['level'] == d3.select(this).text() ),
        html_id2=html_id + "_2",
        title='Decision Level: ' + d3.select(this).text(),
      );
    });
  }*/






  // ----- Add X-Axis Label to plot ----->
  if(xaxis.label.value != null){
      g_chart.append("text")
        .attr("class", "xaxis.label.value")
        .style("font-family", font.family)
        .style("font-size", xaxis.label.size + "px")
        .style('font-weight', xaxis.label.weight)
        .style("text-anchor", "middle")
        .style("dominant-baseline", "hanging")
        .attr('x', xScale.range()[0] + ((xScale.range()[1] - xScale.range()[0])*0.5) )
        .attr("y", (yaxis.offset.top + height.yaxis + yaxis.offset.bottom + (xaxis.tick.size*1.1) + 15))
        .text(xaxis.label.value)
        .call(splitWrapTextSpan, (xScale.range()[1] - xScale.range()[0]), xaxis.label.size, xaxis.label.weight, font.family, valign='bottom', dy_extra=0);
  }


  // ----- Add X-Axis to plot ----->
  if(xaxis.show){
    var x_axis_chart = g_chart.append("g")
        .attr("class", "x_axis")
        .style("font-size", xaxis.tick.size + "px")
        .attr("transform", "translate(" + 0 + "," + (yaxis.offset.top + height.yaxis + yaxis.offset.bottom) + ")")
        .call(xAxisChart);

    // Remove Axis Line
    if(!xaxis.show_line){
      x_axis_chart.select(".domain").remove();
    }

    // Remove Axis Ticks
    if(!xaxis.show_ticks){
      x_axis_chart.selectAll(".tick").selectAll("line").remove();
    }

    if(xaxis.show_grid){
      x_axis_chart.selectAll(".tick line").attr("stroke", "#d3d2d2");
    }
  }






    // ----- Add Bars, CI and Text to plot ----->
    dataPlot.forEach(function(vData, iData){

      //  var facetPos = 0;

        vData[0].forEach(function(vFacet, iFacet){
          //console.log('MEH', vFacet)


          var g_facet = svg.select('.g_scroll_' + iData)
            .append('g')
            .attr("class", 'facet_' + iFacet)
            //.attr('transform', `translate(${0}, ${facetPos})`)
            .attr('transform', `translate(${0}, ${facet_ypos[iFacet]})`)

          //facetPos += (height.yaxis*(domainFacet[iFacet]['y'].length/domainY.length));


          if(facet.var != null){
            g_facet.selectAll('facet_text')
                .data(splitWrapText(domainFacet[iFacet]['facet'], (canvas_width - margin.left - margin.right), fontSize=facet.size, fontWeight=facet.weight, fontFamily=font.family))
                .enter()
                .append("text")
                  .style("font-family", font.family)
                  .style("font-size", facet.size +  "px")
                  .style('font-weight', facet.weight)
                  .style("text-anchor", "middle")
                  .style("dominant-baseline", "hanging")
                  .attr("class", "facet_text")
                  //.attr('x', margin.left + ((canvas_width - margin.left - margin.right)/2))
                  .attr('x', ((canvas_width - margin.left - margin.right)/2))
                  .attr("dy", function(d, i){ return i*1.1 + 'em'})
                  .attr('transform', `translate(${0}, ${-height.facetLabel[iFacet]})`)
                  .text(d => d);

          }




          // ----- Add Y-Axis to plot ----->
          if(yaxis.show){
            var y_axis_chart = g_facet.append("g")
                .attr("class", "y_axis")
                .style("font-size", yaxis.tick.size + "px")
                .attr("transform", "translate(" + (margin.yaxislabel+margin.yaxis) + "," + 0 + ")")
                .call(yAxisChart[iFacet]);


            y_axis_chart.selectAll(".tick text")
                .attr("y", '0.0')
                .call(splitWrapTextSpan, ((canvas_width*0.4) - (margin.left + margin.yaxislabel)), yaxis.tick.size, yaxis.tick.weight, font.family, valign='center', dy_extra=0.32);

            // Remove Axis Line
            if(!yaxis.show_line){
              y_axis_chart.select(".domain").remove();
            }

            // Remove Axis Ticks
            if(!yaxis.show_ticks){
              y_axis_chart.selectAll(".tick").selectAll("line").remove();
            }


            // Show model text in separate div when click on y-axis elements
            y_axis_chart.selectAll(".tick").selectAll("text")
            .on("click",function(d, i) {

              text_sim_decisions(
                data = data_sim_model_text.filter(d => d['simname'] == simSelector.value && d['level'] == d3.select(this).text() ),
                html_id2=html_id + "_2",
                title='Decision Level: ' + d3.select(this).text(),
              );
            });
          }
          // <----- Add Y-Axis to plot -----




          var g_data = g_facet.selectAll('.bar_rect')
            .data(vFacet)
            .enter()
            .append('g')
              .attr("class", function(d, i){
                return 'scroll_' + iData +
                ' switcher_0' +
                ' group_' + domainGroup.map(d => d['group']).indexOf(d['group']) +
                ' obs_' + iData + '_0_' + domainGroup.map(d => d['group']).indexOf(d['group']) + '_' + i +
                ' level level_' + domainY.indexOf(d['y']) +
                ' facet_' + domainFacet.map(d => d['facet']).indexOf(d['facet'])
              })
              //.append('g')
              //  .attr("class", function(d, i){
              //    return 'facet_' + domainFacet.map(d => d['facet']).indexOf(d['facet'])
              //  })
              .attr('startRect', d => xScale(d['startRect']))
              .attr('endRect', d => xScale(d['endRect']))
              .attr('widthRect', d => xScale(d['endRect']) - xScale(d['startRect']))
              .attr('color-value', d => d[clr_var])
              .attr('group-value', function(d){
                if(group.var != null){ return d['group'] }
                else{ return null }
              })
              .attr('x-value', d => d['x'])
              .attr('y-value', function(d, i){
                if(barmode == 'group'){ return yScale[iFacet](d['y']) + (yScale[iFacet].bandwidth()*(domainGroup.map(d => d['group']).indexOf(d['group'])/domainGroup.length)) }
                else{ return yScale[iFacet](d['y']) }
              })
              .style("opacity", 1.0)
              .on('mouseover', (event, d) => {

                        // ----- Tooltip ----->
                        var thisX = +event.currentTarget.getAttribute("startRect") + (+event.currentTarget.getAttribute("widthRect")/2) + margin.left;
                        var thisY = +event.currentTarget.getAttribute("y-value") + (margin.top + height.title + height.scroll + height.switcher + height.legend);


                        var maxTextWidth = 0;
                        var rectHeight = 0;
                        var hoverText = [];
                        /*if(group.var != null){
                          hoverText.push({
                            'value':event.currentTarget.getAttribute("group-value"),
                            'size':group.size,
                            'weight':group.weight
                          })

                          rectHeight += (group.size*1.1);
                          maxTextWidth = (textWidth(event.currentTarget.getAttribute("group-value"), group.size, group.weight) > maxTextWidth)? textWidth(event.currentTarget.getAttribute("group-value"), group.size, group.weight): maxTextWidth;
                        }*/

                        /*if(tooltip.text != null){
                            var scrollIndex = event.currentTarget.getAttribute("class").split(' ')[0].split('_')[1]
                            var switcherIndex = event.currentTarget.getAttribute("class").split(' ')[1].split('_')[1]
                            var facetIndex = event.currentTarget.getAttribute("class").split(' ')[6].split('_')[1]
                            var obsIndex = event.currentTarget.getAttribute("class").split(' ')[3].split('_')[4]

                            thisY += facet_ypos[facetIndex]

                            var dataPoint = dataPlot[scrollIndex][switcherIndex][facetIndex][obsIndex]


                            tooltip.text.forEach(function(v2, i2, a2){

                              var val = ((v2['prefix'] != null)?v2['prefix']:'') + ((v2['var'] != null)?(d3.format(v2['format'])(dataPoint[v2['var']])): '') + ((v2['suffix'] != null)?v2['suffix']:'');

                              hoverText.push({
                                'value': val,
                                'size': yaxis.tick.size,
                                'weight': yaxis.tick.weight
                              });

                              rectHeight += (yaxis.tick.size*1.1);
                              maxTextWidth = (textWidth(val, yaxis.tick.size, yaxis.tick.size) > maxTextWidth)? textWidth(val, yaxis.tick.size, yaxis.tick.size): maxTextWidth;
                            })
                        }
                        else{
                          hoverText.push(event.currentTarget.getAttribute("x-value"));

                          rectHeight += (yaxis.tick.size*1.1);
                          maxTextWidth = (textWidth(event.currentTarget.getAttribute("x-value"), yaxis.tick.size, yaxis.tick.size) > maxTextWidth)? textWidth(event.currentTarget.getAttribute("x-value"), yaxis.tick.size, yaxis.tick.size): maxTextWidth;
                        }*/


                        if(tooltip_text != null){
                          var scrollIndex = event.currentTarget.getAttribute("class").split(' ')[0].split('_')[1]
                          var switcherIndex = event.currentTarget.getAttribute("class").split(' ')[1].split('_')[1]
                          var facetIndex = event.currentTarget.getAttribute("class").split(' ')[6].split('_')[1]
                          var obsIndex = event.currentTarget.getAttribute("class").split(' ')[3].split('_')[4]

                          thisY += facet_ypos[facetIndex]

                          var dataPoint = dataPlot[scrollIndex][switcherIndex][facetIndex][obsIndex]

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
                              'value': val,
                              'size': vTooltipLine.size,
                              'weight': vTooltipLine.weight
                            });
                          })
                        }
                        else{
                          hoverText.push(event.currentTarget.getAttribute("x-value"));

                          rectHeight += (yaxis.tick.size*1.1);
                          maxTextWidth = (textWidth(event.currentTarget.getAttribute("x-value"), yaxis.tick.size, yaxis.tick.weight) > maxTextWidth)? textWidth(event.currentTarget.getAttribute("x-value"), yaxis.tick.size, yaxis.tick.weight): maxTextWidth;
                        }



                        if((thisX + (maxTextWidth*0.5) + 5) > (canvas_width - margin.right)){
                          var shift_left = Math.abs((canvas_width - margin.right) - (thisX + (maxTextWidth*0.5) + 5))
                        };

                        g_tooltip
                            .style('opacity', 1)
                            .attr('transform', `translate(${(thisX-(shift_left || 0))}, ${(thisY-rectHeight-3)})`)

                        tooltipRect.attr("stroke", function(){
                            if(event.currentTarget.getAttribute("color-value") == 'white' || event.currentTarget.getAttribute("color-value") == "rgb(255,255,255)" || event.currentTarget.getAttribute("color-value") == "#fff" || event.currentTarget.getAttribute("color-value") == "#ffffff"){
                              return '#d3d2d2'
                            }
                            else{
                              return event.currentTarget.getAttribute("color-value")
                            }
                          })
                          .attr("width", maxTextWidth + 20)
                          .attr("height", rectHeight+6)
                          .attr("x", -((maxTextWidth + 20)*0.5));

                        tooltipText.selectAll('tspan').remove();

                        var dy = 0;
                        hoverText.forEach(function(vHover, iHover){
                          tooltipText.append('tspan')
                              .style("font-size", vHover['size'])
                              .style("font-weight", vHover['weight'])
                              .attr("x", 0)
                              .attr("y", 0)
                              .attr("dy", dy + 'px')
                              .text(vHover['value']);

                          dy += 1.1*vHover['size'];
                        })

                        // <----- Tooltip -----


              })
              .on('mouseout', (event, v) => {
                      g_tooltip.style('opacity', 0).attr("transform", "translate(" + 0 + "," + 0 +")");
              });



          // ----- Add Bars ----->
          g_data.append('rect')
              .attr("class", function(d){
                return 'bar_rect group_' + domainGroup.map(d => d['group']).indexOf(d['group'])
              })
              .attr("fill", function(d){ return d['clr'] })
              .attr("x", function(d){ return xScale(d['startRect']) })
              .attr('x-value', d => d['x'])
              .attr("y", function(d, i){
                if(barmode == 'group'){
                  return (yScale[iFacet](d['y']) + (yScale[iFacet].bandwidth()/2) - (height.bar/2)) + (barShiftScale(domainGroup.map(d => d['group']).indexOf(d['group'])))
                }
                else{
                  //return yScale(d['y']) + (yScale.bandwidth()/2) - (height.bar/2)
                  if(bar.height.var != null){
                    return yScale[iFacet](d['y']) + (yScale[iFacet].bandwidth()/2) - (Math.max(10, height.bar*(d[bar.height.var]/maxBarHeightVal[domainScroll.indexOf(d['scroll'])][domainSwitcher.indexOf(d['switcher'])]))/2)
                  }
                  else{
                    return yScale[iFacet](d['y']) + (yScale[iFacet].bandwidth()/2) - (height.bar/2)
                  }
                }
              })
              .attr("width", function(d){ return 0 })
              //.attr("height", function(d){
              //  return height.bar
              //})
              .attr("height", function(d){
                if(bar.height.var != null){
                  return Math.max(10, height.bar*(d[bar.height.var]/maxBarHeightVal[domainScroll.indexOf(d['scroll'])][domainSwitcher.indexOf(d['switcher'])]))
                }
                else{
                  return height.bar
                }
              })
              .style("opacity", 1.0)
              .transition()
              .delay(function(d){ return (domainGroup.map(d => d['group']).indexOf(d['group'])*200) + (domainY.indexOf(d['y'])*100) })
              .duration(800)
                .attr('width', function(d) { return xScale(d['endRect']) - xScale(d['startRect']) });





          // ----- Add text to bars ----->
          if(bar.text != null){

              var g_bar_text = g_data.append("text")
                    .attr("class", function(d){
                      return 'bar_text group_' + domainGroup.map(d => d['group']).indexOf(d['group'])
                    })
                    .style('fill', function(d){
                      if(barmode=='stack'){
                        if(lightOrDark(d['clr']) == 'light'){ return 'black'}
                        else{ return 'white' }
                      }
                      else{ return 'black' }
                    })
                    .style("font-family", font.family)
                    //.style("font-size", yaxis.tick.size + "px")
                    .style("font-size", function(d){
                      if(bar.height.var != null && Math.max(10, (height.bar*(d[bar.height.var]/maxBarHeightVal[domainScroll.indexOf(d['scroll'])][domainSwitcher.indexOf(d['switcher'])]))) < ((yaxis.tick.size*1.1)*bar.text.length)){
                        return (Math.max(10/bar.text.length, (height.bar*(d[bar.height.var]/maxBarHeightVal[domainScroll.indexOf(d['scroll'])][domainSwitcher.indexOf(d['switcher'])]))/bar.text.length) /1.1 ) + "px";
                      }
                      else{
                        return yaxis.tick.size + "px";
                      }
                    })
                    .style('font-weight', yaxis.tick.weight)
                    .style('text-anchor', (barmode == 'group')? 'start': 'middle')
                    .style("dominant-baseline", "hanging")
                    .attr("x", function(d){ return xScale(d['startRect']) })
                    .attr("y", function(d, i){
                      if(barmode == 'group'){
                        //return (yScale(d['y']) + (yScale.bandwidth()*(domainGroup.map(d => d['group']).indexOf(d['group'])/domainGroup.length)) + (yScale.bandwidth()*(1/(domainGroup.length*2))) )
                        return (yScale[iFacet](d['y']) + (yScale[iFacet].bandwidth()/2)) + (barShiftScale(domainGroup.map(d => d['group']).indexOf(d['group'])))
                      }
                      else{
                        return yScale[iFacet](d['y']) + (yScale[iFacet].bandwidth()/2)
                      }
                    })
                    .attr('transform', `translate(${(barmode=='group')?5:0}, ${0})`)
                    .each(d => d)
                    .call(barText, yaxis.tick.size);


              svg.select('.g_scroll_' + iData).selectAll(".bar_text").selectAll('tspan')
                .transition()
                .delay(function(d){ return (domainGroup.map(d => d['group']).indexOf(d['group'])*200) + (domainY.indexOf(d['y'])*100) })
                .duration(800)
                .style("opacity", 1)
                .attr('x', function(d){
                  if(barmode == 'group'){
                    return xScale(d['endRect'])
                  }
                  else{
                    return xScale(d['startRect']) + ((xScale(d['endRect']) - xScale(d['startRect']))/2)
                  }

                });

        }

      })
    });







  // <---------------------
  // <----- BAR CHART -----
  // <---------------------









  // ----------------------->
  // ----- SKILLS DATA ----->
  // ----------------------->

  if(data_skills != undefined){

    var domainSkills = Array.from(new Set(data_skills.map(d => d[skill.var])));
    var data_skills = d3.group(data_skills, d => d[skill.var]);

    var dataSkillsFinal = []
    domainSkills.forEach((v, i) => {
      var g_skill_classes = '';
      Array.from(data_skills.get(v).map(d => d[y.var])).forEach((v2, i2) => {
        g_skill_classes = g_skill_classes.concat(' level_' + domainY.indexOf(v2));
      })

      dataSkillsFinal.push({'skill': v, 'classes': g_skill_classes});
    })




    function textSize(text, fontFace=font.family, fontSize=16, fontWeight=700) {
        if (!d3) return;
        var container = d3.select('body').append('svg').attr("class", "textSizeCalc");
        container.append('text')
          .attr("x", -99999)
          .attr("y", -99999)
          .style("font-family", fontFace)
          .style("font-size", fontSize + "px")
          .style("font-weight", fontWeight)
          .text(text);

        var size = container.node().getBBox();
        container.remove();

        return { width: size.width, height: size.height };
    }


    function idealSkillSizes(
      data=dataSkillsFinal,
      fontFace = font.family,
      maxfontSize=16,
      requiredHeight=height.legend + yaxis.offset.top + height.yaxis + yaxis.offset.bottom
    ){
      // Loop down through fontsizes to find the first one that will fit all skills in
      var idealFontSize = maxfontSize;
      for(let fontSize = maxfontSize; fontSize > 0; fontSize--){

        idealFontSize = fontSize;

        //var numLines = 0;
        var totalHeight = 0;

        data.forEach((v, i) => {
            v['y'] = totalHeight;
            v['fontSize'] = fontSize;
            //var numLines = text_numlines(v['skill'], (200*0.9), fontSize=fontSize, fontWeight=700, fontFace=fontFace);
            var numLines = splitWrapText(v['skill'], width=(200*0.9), fontSize=fontSize, fontWeight=700, fontFamily=fontFace).length
            totalHeight += (numLines*textSize(v['skill'], fontFace=fontFace, fontSize=fontSize).height) + textSize(v, fontFace=font.family, fontSize=fontSize).height
        })

        if (totalHeight < requiredHeight){ return idealFontSize; }
      };
    }
    var skillFontSize = idealSkillSizes();

    //console.log('skillFontSize', skillFontSize);
    //console.log('dataSkillsFinal:', dataSkillsFinal)

  }

  // <-----------------------
  // <----- SKILLS DATA -----
  // <-----------------------






  // -------------------------->
  // ----- SKILLS SIDEBAR ----->
  // -------------------------->

  if(data_skills != undefined){

    var g_skills = svg.append('g')
        .attr('class', 'g_skills')
        .attr('x', margin.left)
        .attr('y', margin.top)
        .attr('transform', `translate(${(canvas_width)}, ${0})`);



    g_skills.append('rect')
      .attr('x', 0)
      .attr('y', 0)
      .attr('width', 200)
      .attr('height', canvas_height - (margin.top + margin.bottom))
      .attr('fill', '#d3d2d2') // light gray
      /*.on('mouseout', (event, v) => {
                if(g_skills.node().transform.baseVal.getItem(0).matrix.e < canvas_width){
                  g_skills.transition()
                  .duration(500)
                  .attr('transform', `translate(${canvas_width}, ${0})`);
                }
      })*/
      .on('click', (event, v) => {
                d3.selectAll('.skill_text').style('font-weight', 'normal')
                g_chart.selectAll('g').style('opacity', 1.0);
                //svg.selectAll('.bar_rect').style('opacity', 1.0);
                //svg.selectAll('.bar_text').style('opacity', 1.0);
      })



    g_skills.append('circle')
      .attr('cx', 0)
      .attr('cy', height.title + height.scroll + (height.switcher/2))
      .attr('r', height.switcher/2)
      .attr('fill', '#d3d2d2') // light gray
      .on('mouseover', (event, v) => {

            if(g_skills.node().transform.baseVal.getItem(0).matrix.e ==  canvas_width){
              g_skills.transition()
              .duration(500)
              .attr('transform', `translate(${canvas_width-200}, ${0})`);
            }
      })


    g_skills.selectAll('.skill_text')
      .data(dataSkillsFinal)
        .enter()
        .append('g')
        .attr('class', function(d){ return d['classes']})
        .attr('transform', function(d){ return `translate(${0}, ${height.title + height.scroll + height.switcher + d['y']})` } )
        //.on('mouseover', (event, v) => {
        //      g_skills.transition()
        //        .duration(500)
        //        .attr('transform', `translate(${canvas_width-200}, ${0})`);
        //})
        .append('text')
          .attr('class', function(d){ return 'skill_text' + d['classes']})
          .style("font-family", font.family)
          .style("font-size", function(d){ return d['fontSize'] + 'px' })
          .style('font-weight', 'normal')
          .style('text-anchor', 'middle')
          .attr('x', 200*0.5)
          .attr("y", 0 )
          .attr("dy", '1.00em')
          .text(function(d){ return d['skill']})
          //.call(splitWrapText, (200*0.9), fontSize=skillFontSize, fontWeight=400, fontFace=font.family)
          .call(splitWrapTextSpan, (200*0.9), skillFontSize, 400, font.family, valign='bottom', dy_extra=0)
          .on("click", function() {
            var filteredClasses = '.' + d3.select(this).attr('class').split(' ').slice(1).join(",.");

            d3.selectAll('.skill_text').style('font-weight', '400')
            d3.select(this).style('font-weight', '700');

            // Highlight Bars
            g_chart.selectAll('.level').style('opacity', 0.2);
            //g_chart.selectAll('.bar_text').style('opacity', 0.2);
            g_chart.selectAll(filteredClasses).style('opacity', 1.0);

            // Highlight Bar Text
            //g_chart.selectAll('.bar_text').style('opacity', 0.2);
            //g_chart.selectAll(filteredClasses).style('opacity', 1.0);
          });




    // --- White rectangle to cover gray skills area (to account for user zooming out) --->
    svg.append('g')
        .attr('x', margin.left)
        .attr('y', margin.top)
        .attr('transform', `translate(${(canvas_width)}, ${0})`)
          .append('rect')
            .attr('x', 0)
            .attr('y', 0)
            .attr('width', 200)
            .attr('height', canvas_height - (margin.top + margin.bottom))
            .attr('fill', 'white');
    // <--- White rectangle to cover gray skills area (to account for user zooming out) ---
  }

  // <--------------------------
  // <----- SKILLS SIDEBAR -----
  // <--------------------------











  // ------------------->
  // ----- TOOLTIP ----->
  // ------------------->

  var g_tooltip = svg.append("g")
    .attr("class", "tooltip_" + html_id.slice(1))
    .style('opacity', 0);

  var tooltipRect = g_tooltip.append('rect')
      .attr("class", "tooltip_" + html_id.slice(1) + "__rect")
      .attr('x', 0)
      .attr('y', -3)
      .attr('width', 0)
      .attr('height', 0)
      .attr("fill", "white")
      .attr("stroke", "black")
      .attr("stroke-width", "2");

  var tooltipText = g_tooltip.append('text')
    .style("text-anchor", "middle")
    .style("dominant-baseline", "hanging")
    .attr("class", "tooltip_" + html_id.slice(1) + "__text")
    .style("font-family", font.family)
    .attr('x', 0)
    .attr('y', 0)

  // <-------------------
  // <----- TOOLTIP -----
  // <-------------------





  // ---------------------->
  // ----- Zoom & Pan ----->
  // ---------------------->

  let zoom = d3.zoom()
    .on('zoom', handleZoom)
    .scaleExtent([0.5, 1])
    .translateExtent([[0, 0], [canvas_width, canvas_height]]);

  function handleZoom(e) {
    d3.select(html_id + ' svg g')
      .attr('transform', e.transform);
  }

  d3.select(html_id + ' svg')
    .call(zoom);

  // <----------------------
  // <----- Zoom & Pan -----
  // <----------------------


}
