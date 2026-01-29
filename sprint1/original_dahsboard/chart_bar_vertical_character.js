function chart_bar_vertical_character(
  data,
  html_id,

  x={var:{start:null, end:null}, order:'as_appear', ascending:true}, // Must be categorical
  y={var:null, ascending:true, ci:[null, null]}, // Must be numeric

  title={value:[{size:40, weight:700, text:null}, {size:32, weight:700, text:null}], line:false},

  clr={
    var:'clr',
    palette:null, // 'plotly', 'd3', 'g10', 't10', 'alphabet', 'dark24', 'light24', 'set1', 'pastel1'
    value:'#e32726'
  }, // Variable containing color of bar(s), a name of a pre-defined palette of colors, or value to set all bars to same color
  opacity={var:null, value:1.0}, // Variable containing opacity of bar(s) or value to set all bars to same opacity

  facet={var:null, size:18, weight:400, space_above_title:5, order:'as_appear', ascending:true, line:{show:false, color:'#d3d2d2'}},
  group={var:null, label:{value:null, size:18, weight:700}, size:18, weight:400, order:'as_appear', ascending:true, show:true},
  switcher={var:null, label:{value:null, size:18, weight:700}, size:18, weight:400, order:'as_appear', ascending:true, line:false},
  scroll={var:null, label:{value:null, size:20, weight:700}, size:18, weight:400, order:'as_appear', ascending:true, line:false},

  bar={
    size:16, weight:400,
    text:null, // Array of arrays: [{var:'n', format:',', prefix:null, suffix:null}, {var:'pct', format:'.1f', prefix:null, suffix:'%'}]
    maxWidth:20
  },

  tooltip_text=[
    {size:14, weight:400, text:[{var:'pct', format:'.1f', prefix:null, suffix:'%'}]},
    {size:14, weight:400, text:[
      {var:'n', format:',.0f', prefix:null, suffix:null},
      {var:'tot', format:',.0f', prefix:'/', suffix:null}
    ]}
  ],

  barmode='group', // 'group', 'overlay' or 'stack'

  hline={
    var:{name:'bench', line_style:'dashed', clr:'black', width:2},
    value:[
      {y:50, line_style:'dashed', clr:'black', width:2}
    ]
  },

  xaxis={
    label:{value:null, size:20, weight:700},
    offset: {left:10, right:10},
    tick:{size:14, weight:400, orientation:'h', splitWidth:150},
    show:true,
    show_line:true,
    show_ticks:true,
  },

  yaxis={
    height:400,
    label:{value:null, size:20, weight:700},
    offset: {top:10, bottom:10},
    range:[null, null],
    rangeScroll:'fixed', // 'fixed' or 'free'
    rangeFacet:'fixed', // 'fixed' or 'free'
    suffix:null,
    format:null,
    tick:{size:14, weight:400, width:150},
    show:true,
    show_line:true,
    show_ticks:true,
    num_ticks:null,
    show_grid:false
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





  // -------------------------------------------------------->
  // ----- Function to add TSPAN for each split-up text ----->
  // -------------------------------------------------------->

  function splitWrapTextSpan(text, width=100, fontSize=14, fontWeight=400, fontFamily=font.family, valign='bottom', dy_extra=0) {

    text.each(function() {

      var text = d3.select(this),
          lineNumber = 0,
          lineHeight = 1.1, // ems
          yThis = text.attr('y'),
          xThis = text.attr('x'),
          dy = parseFloat(text.attr('dy')),
          textSplit = splitWrapText(text.text(), width=width, fontSize=fontSize, fontWeight=fontWeight, fontFamily=fontFamily),
          tspan = text.text(null);

      var vshift = (valign == 'bottom')? 0: (valign == 'top')? (1.1): (1.1/2)

      textSplit.forEach(function(v, i, a){

          text.append('tspan')
              .attr('x', xThis)
              .attr('y', yThis)
              .attr('dy', `${((i * lineHeight) - ((a.length-1)*vshift) + (dy_extra))}em`)
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
            'dy': Math.min(1.1, (iTextSplit*1.1)) + 'em',
            'this-width-value': thisWidth,
            //'max-width-value': maxTextWidth
          })
        })

        listSplitWrappedText.forEach(function(vListSplitWrappedText, iListSplitWrappedText){
          vListSplitWrappedText['max-width-value'] = maxTextWidth;
        });

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





  // ---------------------------------------->
  // ----- Function to add text to bars ----->
  // ---------------------------------------->

  function barText(d, iScroll, iFacet){

    d.each(function(v, i){

        var text = d3.select(this)
        var lineHeight = 1.1; // ems
        var yThis = text.attr('y');
        var xThis = text.attr('x');
        var groupThis = text['_groups'][0][0].getAttribute('class').split(' ')[1]
        var visibilityThis = svg.selectAll('.' + groupThis).attr('visibility');


        bar.text.forEach(function(v2, i2, a2){

          var text_val = ((v2['prefix'] != null && v[v2['var']] != null)?v2['prefix']:'') + ((v2['var'] != null)?((v[v2['var']] != null)?d3.format(v2['format'])(v[v2['var']]): ''): '') + ((v2['suffix'] != null && v[v2['var']] != null)?v2['suffix']:'');

          text.append('tspan')
              .attr('opacity', 1.0)
              .attr('visibility', function(d){
                  //'visible'
                  return visibilityThis
              })
              .attr('class', function(d){ return 'tspan_' + i2 + ' ' + groupThis })
              .attr('x', xThis)
              .attr('y', yThis)
              //.attr('transform', d => `rotate(-90, ${xThis}, ${yThis})`)
              .attr('text-value', v[v2['var']])
              .attr('rect-height', function(d){
                return xScale[iScroll][iFacet](v['rectTop']) - xScale[iScroll][iFacet](v['rectBottom'])
              })
              .attr('dy', `${(i2 * lineHeight) - ((1.1/2)*(bar.text.length))}em`)
              .text(function(){
                if(barmode == 'stack'){
                  if(textWidth(text_val, fontSize=v['font-size'], fontWeight=bar.weight, fontFamily=font.family) < ((yScale[iScroll][iFacet](v['rectBottom']) - yScale[iScroll][iFacet](v['rectTop']))-6)){
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

  function barTransition(d, iScroll, iFacet){

    d.each(function(v, i){

        var text = d3.select(this)
        //var lineHeight = 1.1; // ems
        var y = text.attr('y');

        //var x = text.attr('x');

        bar.text.forEach(function(v2, i2, a2){

          //var text_val = ((v2['prefix'] != null)?v2['prefix']:'') + ((v2['var'] != null)?(d3.format(v2['format'])(v[v2['var']])): '') + ((v2['suffix'] != null)?v2['suffix']:'');

          text.transition()
              .duration(800)
              /*.attr('x', d => xScale[iScroll][iFacet](d['rectLeft']) + ((xScale[iScroll][iFacet](d['rectRight']) - xScale[iScroll][iFacet](d['rectLeft']))/2))
              .attr('y', function(d){
                if(barmode == 'stack'){
                  return Math.max(yScale[iScroll][iFacet](v['rectTop']), yScale[iScroll][iFacet](v['rectBottom'])) + ((Math.abs(yScale[iScroll][iFacet](v['rectBottom']) - yScale[iScroll][iFacet](v['rectTop'])))/2)
                }
                else{
                  //if(x.ci[0] != null && x.ci[1] != null){
                  //  return xScale[iScroll][iFacet](v['x_ci_u'])
                  //}
                  //else{
                    return yScale[iScroll][iFacet](v['rectTop'])-5
                  //}
                }
              })*/
              /*.attr('transform', function(d){
                if(barmode == 'stack'){
                  return `translate(${Math.max(yScale[iScroll][iFacet](v['rectTop']), yScale[iScroll][iFacet](v['rectBottom'])) + ((Math.abs(yScale[iScroll][iFacet](v['rectBottom']) - yScale[iScroll][iFacet](v['rectTop'])))/2)}, ${Math.max(yScale[iScroll][iFacet](v['rectTop']), yScale[iScroll][iFacet](v['rectBottom'])) + ((Math.abs(yScale[iScroll][iFacet](v['rectBottom']) - yScale[iScroll][iFacet](v['rectTop'])))/2)})`
                }
                else{
                    return `translate(${Math.max(yScale[iScroll][iFacet](v['rectTop']), yScale[iScroll][iFacet](v['rectBottom'])) + ((Math.abs(yScale[iScroll][iFacet](v['rectBottom']) - yScale[iScroll][iFacet](v['rectTop'])))/2)}, ${yScale[iScroll][iFacet](v['rectTop'])-5})`
                }
              });*/
              .attr('transform', function(d){
                if(barmode == 'stack'){
                  return `translate(0, ${Math.max(yScale[iScroll][iFacet](v['rectTop']), yScale[iScroll][iFacet](v['rectBottom'])) + ((Math.abs(yScale[iScroll][iFacet](v['rectBottom']) - yScale[iScroll][iFacet](v['rectTop'])))/2)})`
                }
                else{
                    return `translate(0, ${ - yScale[iScroll][iFacet](v['rectTop'])})`
                }
              });


          text.select(".tspan_" + i2)
              .transition()
              .duration(800)
              .attr('text-value', v[v2['var']])
              .attr('rect-height', function(d){
                return yScale[iScroll][iFacet](v['rectBottom']) - yScale[iScroll][iFacet](v['rectTop'])
              })
              /*.attr('y', function(d){
                if(barmode == 'stack'){
                  return Math.max(yScale[iScroll][iFacet](v['rectTop']), yScale[iScroll][iFacet](v['rectBottom'])) + ((Math.abs(yScale[iScroll][iFacet](v['rectBottom']) - yScale[iScroll][iFacet](v['rectTop'])))/2)
                }
                else{
                  //if(x.ci[0] != null && x.ci[1] != null){
                  //  return xScale[iScroll][iFacet](v['x_ci_u'])
                  //}
                  //else{
                    return yScale[iScroll][iFacet](v['rectTop'])-5
                  //}
                }
              })*/
              /*.attr('transform', function(d){
                if(barmode == 'stack'){
                  return `rotate(-90, ${xScale[iScroll][iFacet](v['rectLeft'])}, ${Math.max(yScale[iScroll][iFacet](v['rectTop']), yScale[iScroll][iFacet](v['rectBottom'])) + ((Math.abs(yScale[iScroll][iFacet](v['rectBottom']) - yScale[iScroll][iFacet](v['rectTop'])))/2)})`
                }
                else{
                    return `rotate(-90, ${xScale[iScroll][iFacet](v['rectLeft'])}, ${yScale[iScroll][iFacet](v['rectTop'])-5})`
                }
              })*/
              .textTween(function(d) {
                const element = this;
                const initialTextValue = parseFloat(element.getAttribute('text-value'));
                const initialRectHeight = parseFloat(element.getAttribute('rect-height'));
                const i = d3.interpolate(initialTextValue, v[v2['var']]);
                const j = d3.interpolate(initialRectHeight, Math.abs(xScale[iScroll][iFacet](v['rectBottom']) - xScale[iScroll][iFacet](v['rectTop'])));

                //const i = d3.interpolate($(this).attr('text-value'), v[v2['var']]);
                //const j = d3.interpolate($(this).attr('rect-height'), Math.abs(yScale[iScroll][iFacet](v['rectBottom']) - yScale[iScroll][iFacet](v['rectTop'])));
                return function(t) {

                  if(barmode == 'stack'){
                    if(isNaN(parseFloat(i(t)))){
                      return ' ';
                    }
                    else if( textWidth(
                          //text=parseFloat(i(t)).toFixed(1) + '%',
                          text=((v2['prefix'] != null && i(t) != null)?v2['prefix']:'') + ((v2['var'] != null)?(d3.format(v2['format'])(parseFloat(i(t)))): '') + ((v2['suffix'] != null && i(t) != null)?v2['suffix']:''),
                          fontSize=v['font-size'], //bar.size,
                          fontWeight=bar.weight,
                          fontFamily=font.family
                      ) < (j(t)-6) ){
                        if(parseFloat(i(t)) != null){
                          return ((v2['prefix'] != null && i(t) != null)?v2['prefix']:'') + ((v2['var'] != null)?(d3.format(v2['format'])(parseFloat(i(t)))): '') + ((v2['suffix'] != null && i(t) != null)?v2['suffix']:'');
                        }
                        else{
                          return ' ';
                        }
                    }
                    else { return ' '; }
                  }
                  else{
                    if(isNaN(parseFloat(i(t)))){
                        return ' ';
                    }
                    else{
                      return ((v2['prefix'] != null && i(t) != null)?v2['prefix']:'') + ((v2['var'] != null)?(d3.format(v2['format'])(parseFloat(i(t)))): '') + ((v2['suffix'] != null && i(t) != null)?v2['suffix']:'');
                    }
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

    dataPlot.forEach(function(vScroll, iScroll){
      vScroll.forEach(function(vFacet, iFacet){

            svg.selectAll('.scroll_' + iScroll)
              .filter('.facet_' + iFacet)
              .data(vFacet[iSwitch])
                .transition()
                .attr('class', function(d, i){
                  return 'scroll_' + iScroll +
                  ' switcher_' + iSwitch +
                  ' facet_' + iFacet +
                  ' group_' + domainGroup.map(d => d['group']).indexOf(d['group']) +
                  ' obs_' + iScroll + '_' + iSwitch + '_' + iFacet + '_' + domainGroup.map(d => d['group']).indexOf(d['group']) + '_' + i +
                  ' bar'
                })
                .attr('rectTop', d => yScale[iScroll][iFacet](d['rectTop']))
                .attr('rectBottom', d => yScale[iScroll][iFacet](d['rectBottom']))
                .attr('rectLeft', d => xScale[iScroll][iFacet](d['rectLeft']))
                .attr('rectRight', d => xScale[iScroll][iFacet](d['rectRight']))
                .attr('rectWidth', d => xScale[iScroll][iFacet](d['rectRight']) - xScale[iScroll][iFacet](d['rectLeft']))
                .attr('rectHeight', d => yScale[iScroll][iFacet](d['rectBottom']) - yScale[iScroll][iFacet](d['rectTop']))
                .attr('color-value', d => d['clr'])
                .attr('group-value', function(d){
                  if(group.var != null){ return d['group'] }
                  else{ return '' }
                })
                //.attr('cil-value', d => (x.ci[0] != null)? d['x_ci_l']: d['x'])
                //.attr('ciu-value', d => (x.ci[1] != null)? d['x_ci_u']: d['x'])
                .attr('x-value', function(d, i){
                  if(barmode == 'group'){
                    return xScale[iScroll][iFacet](d[x.var.start]) + (xScale[iScroll][iFacet].bandwidth()/2) + barShiftScale[iScroll][iFacet](domainGroup.map(d => d['group']).indexOf(d['group']))
                  }
                  else{
                    //return xScale[iScroll][iFacet](d['rectLeft']) + (xScale[iScroll][iFacet].bandwidth()/2) - ((xScale[iScroll][iFacet].bandwidth()*0.95)/2)
                    return xScale[iScroll][iFacet](d[x.var.start])
                  }
                })
                .attr('y-value', function(d){
                  //if(barmode == 'group'){ return yScale[iScroll][iFacet](d['y']) + (yScale[iScroll][iFacet].bandwidth()*(domainGroup.map(d => d['group']).indexOf(d['group'])/domainGroup.length)) }
                  //else{ return yScale[iScroll][iFacet](d['y']) }
                  yScale[iScroll][iFacet](d['y'])
                });


            svg.select('.g_scroll_' + iScroll)
              .select('.facet_' + iFacet)
              .selectAll('.bar_rect')
              .data(vFacet[iSwitch])
              .transition()
                .duration(800)
                //.attr('cil-value', d => (x.ci[0] != null)? d['x_ci_l']: d['x'])
                //.attr('ciu-value', d => (x.ci[1] != null)? d['x_ci_u']: d['x'])
                .attr('fill', d => d['clr'])
                .attr('opacity', d => d['opacity'])
                .attr('stroke', function(d){
                  if(d['clr'] == 'white' || d['clr'] == 'rgb(255,255,255)' || d['clr'] == '#fff' || d['clr'] == '#ffffff'){
                    return '#d3d2d2'
                  }
                  else{
                    return d['clr']
                  }
                })
                .attr('y', function(d){ return yScale[iScroll][iFacet](d['rectTop']) })
                .attr('height', function(d){ return Math.abs(yScale[iScroll][iFacet](d['rectBottom']) - yScale[iScroll][iFacet](d['rectTop'])) });



            if(bar.text != null){
              // --- Delete current text --->
              svg.select('.g_scroll_' + iScroll).select('.facet_' + iFacet).selectAll('.bar').selectAll('.bar_text').remove();

              // --- Add new text --->
              svg.select('.g_scroll_' + iScroll)
                .select('.facet_' + iFacet)
                .selectAll('.bar')
                .data(vFacet[iSwitch])
                .append('text')
                    .attr('class', function(d){
                      return 'bar_text group_' + domainGroup.map(d => d['group']).indexOf(d['group'])
                    })
                    .style('fill', function(d){
                      if(barmode=='stack'){
                        if(lightOrDark(d['clr']) == 'light'){ return 'black'}
                        else{ return 'white' }
                      }
                      else{
                        if(d['clr'] == 'white' || d['clr'] == 'rgb(255,255,255)' || d['clr'] == '#fff' || d['clr'] == '#ffffff'){
                          return '#d3d2d2'
                        }
                        else{
                          return d['clr']
                        }
                      }
                    })
                    .style('font-family', font.family)
                    .style('font-size', function(d){
                      if(barmode=='group'){
                        if( ((bar.size*1.1)*bar.text.length) <= ( ((xScale[iScroll][iFacet].bandwidth()*0.95)/domainGroup.length)*0.95 ) ){ return bar.size + 'px' }
                        else{
                          return (( ((xScale[iScroll][iFacet].bandwidth()*0.95)/domainGroup.length)*0.95 )/bar.text.length)/1.1 + 'px'
                        }
                      }
                      else{
                        if( ((bar.size*1.1)*bar.text.length) <= (xScale[iScroll][iFacet].bandwidth()*0.95) ){
                          return bar.size + 'px'
                        }
                        else{
                          return ((xScale[iScroll][iFacet].bandwidth()*0.95)/bar.text.length)/1.1 + 'px'
                        }
                      }
                    })
                    .style('font-weight', bar.weight)
                    .style('text-anchor', (barmode == 'overlay' || barmode == 'group')? 'start': 'middle')
                    .style('dominant-baseline', 'hanging')
                    //.attr('cil-value', d => (x.ci[0] != null)? d['x_ci_l']: d['x'])
                    //.attr('ciu-value', d => (x.ci[1] != null)? d['x_ci_u']: d['x'])
                    .attr('opacity', 0.0)
                    .attr('visibility', 'visible')
                    //.attr('x', d => xScale[iScroll][iFacet](d['rectLeft']) + ((xScale[iScroll][iFacet](d['rectRight']) - xScale[iScroll][iFacet](d['rectLeft']))/2) )
                    //.attr('y', d => (barmode == 'overlay' || barmode == 'group')? yScale[iScroll][iFacet](d['rectTop'])-5: yScale[iScroll][iFacet](d['rectTop']) + ((yScale[iScroll][iFacet](d['rectBottom']) - yScale[iScroll][iFacet](d['rectTop']))/2) )
                    //.attr('transform', function(d){
                    // if(barmode=='overlay' || barmode == 'group'){
                    //   return `rotate(-90, ${xScale[iScroll][iFacet](d['rectLeft']) + ((xScale[iScroll][iFacet](d['rectRight']) - xScale[iScroll][iFacet](d['rectLeft']))/2)}, ${yScale[iScroll][iFacet](d['rectTop'])-5})`
                    // }
                    // else{
                    //   return `rotate(-90, ${xScale[iScroll][iFacet](d['rectLeft']) + ((xScale[iScroll][iFacet](d['rectRight']) - xScale[iScroll][iFacet](d['rectLeft']))/2)}, ${yScale[iScroll][iFacet](d['rectTop']) + ((yScale[iScroll][iFacet](d['rectBottom']) - yScale[iScroll][iFacet](d['rectTop']))/2)})`
                    // }
                    //})
                   .attr('x', function(d, i){
                     if(barmode == 'group'){
                       return xScale[iScroll][iFacet](d['x']) + (xScale[iScroll][iFacet].bandwidth()/2) + barShiftScale[iScroll][iFacet](domainGroup.map(p => p['group']).indexOf(d['group']))
                     }
                     else{
                       return xScale[iScroll][iFacet](d['x']) + (xScale[iScroll][iFacet].bandwidth()/2)
                     }
                   })
                   .attr('y', function(d, i){
                      if(barmode == 'group'){
                        return yScale[iScroll][iFacet](d['rectTop'])-5
                      }
                      else if(barmode == 'overlay'){
                        return yScale[iScroll][iFacet](d['rectTop'])-5
                      }
                      else{
                        return yScale[iScroll][iFacet](d['rectTop']) + ((yScale[iScroll][iFacet](d['rectBottom']) - yScale[iScroll][iFacet](d['rectTop']))/2)
                      }
                   })
                   .attr('transform', function(d){
                    if(barmode=='group'){
                       return `rotate(-90, ${xScale[iScroll][iFacet](d['x']) + (xScale[iScroll][iFacet].bandwidth()/2) + barShiftScale[iScroll][iFacet](domainGroup.map(p => p['group']).indexOf(d['group']))}, ${yScale[iScroll][iFacet](d['rectTop'])-5})`
                    }
                    else if(barmode=='overlay'){
                      return `rotate(-90, ${xScale[iScroll][iFacet](d['x']) + (xScale[iScroll][iFacet].bandwidth()/2)}, ${yScale[iScroll][iFacet](d['rectTop'])-5})`
                    }
                    else{
                      return `rotate(-90, ${xScale[iScroll][iFacet](d['x']) + (xScale[iScroll][iFacet].bandwidth()/2)}, ${yScale[iScroll][iFacet](d['rectTop']) + ((yScale[iScroll][iFacet](d['rectBottom']) - yScale[iScroll][iFacet](d['rectTop']))/2)})`
                    }
                  })
                  .each(d => d)
                  .call(barText, iScroll, iFacet)
                    .transition()
                    .delay(800)
                    .duration(200)
                    .attr('opacity', 1.0);
            }



            /*svg.select('.g_scroll_' + iScroll)
              .select('.facet_' + iFacet)
              .selectAll('.bar_text')
              .data(vFacet[iSwitch])
              .each(d => d)
              .call(barTransition, iScroll, iFacet);*/




            /*if(x.ci[0] != null && x.ci[1] != null){
              svg.select('.g_scroll_' + iScroll)
                .select('.facet_' + iFacet)
                .selectAll('.bar_ci')
                .data(vFacet[iSwitch])
                .transition()
                  .duration(800)
                    .attr('x-value', d => d['x'])
                    .attr('cil-value', d => (x.ci[0] != null)? d['x_ci_l']: d['x'])
                    .attr('ciu-value', d => (x.ci[1] != null)? d['x_ci_u']: d['x'])
                    .attr('d', d =>
                    'M' + xScale[iScroll][iFacet](d['x_ci_l']) + ',' + (yScale[iScroll][iFacet](d['y']) + (yScale[iScroll][iFacet].bandwidth()/2) + (barShiftScale(domainGroup.map(d => d['group']).indexOf(d['group']))) - 3) + 'L' +  xScale[iScroll][iFacet](d['x_ci_l']) + ',' + (yScale[iScroll][iFacet](d['y']) + (yScale[iScroll][iFacet].bandwidth()/2) + (barShiftScale(domainGroup.map(d => d['group']).indexOf(d['group']))) + 3)  +
                    'M' + xScale[iScroll][iFacet](d['x_ci_l']) + ',' + (yScale[iScroll][iFacet](d['y']) + (yScale[iScroll][iFacet].bandwidth()/2) + (barShiftScale(domainGroup.map(d => d['group']).indexOf(d['group'])))) + 'L' +  xScale[iScroll][iFacet](d['x_ci_u']) + ',' + (yScale[iScroll][iFacet](d['y']) + (yScale[iScroll][iFacet].bandwidth()/2) + (barShiftScale(domainGroup.map(d => d['group']).indexOf(d['group'])))) +
                    'M' + xScale[iScroll][iFacet](d['x_ci_u']) + ',' + (yScale[iScroll][iFacet](d['y']) + (yScale[iScroll][iFacet].bandwidth()/2) + (barShiftScale(domainGroup.map(d => d['group']).indexOf(d['group']))) - 3) + 'L' +  xScale[iScroll][iFacet](d['x_ci_u']) + ',' + (yScale[iScroll][iFacet](d['y']) + (yScale[iScroll][iFacet].bandwidth()/2) + (barShiftScale(domainGroup.map(d => d['group']).indexOf(d['group']))) + 3) +
                    'M' + xScale[iScroll][iFacet](d['x']) + ',' + (yScale[iScroll][iFacet](d['y']) + (yScale[iScroll][iFacet].bandwidth()/2) + (barShiftScale(domainGroup.map(d => d['group']).indexOf(d['group']))) - 5) + 'L' +  xScale[iScroll][iFacet](d['x']) + ',' + (yScale[iScroll][iFacet](d['y']) + (yScale[iScroll][iFacet].bandwidth()/2) + (barShiftScale(domainGroup.map(d => d['group']).indexOf(d['group']))) + 5)
                    )
            }*/


        //  })
        })
      });

  };

  // <-------------------------------------------
  // <---- Function to change Bars and Text -----
  // <-------------------------------------------










  // ------------------------>
  // ----- DATA DOMAINS ----->
  // ------------------------>


  // --- Scroll domain --->
  var domainScroll = (scroll.var != null)? Array.from(new Set(data.map(d => d[scroll.var]))): [null];
  if(scroll.var != null && scroll.order == 'alphabetical'){ domainScroll.sort(); }
  //console.log('### domainScroll', domainScroll);



  // --- X-axis domain --->
  var domainX = Array.from(new Set(data.map(d => d[x.var.start].toString())));
  if(x.order == 'alphabetical'){ domainX.sort(); }
  if(!x.ascending){ domainX.reverse(); }
  //console.log('domainX', domainX);





  // --- Facet domain --->
  var domainFacet = []
  domainScroll.forEach(function(vScroll, iScroll){
    domainFacet[iScroll] = []

    if(facet.var != null){
      Array.from(new Set(data.filter(d => (scroll.var != null)? (d[scroll.var] == vScroll): true).map(d => d[facet.var].toString()))).forEach(function(vFacet, iFacet){

        if(xaxis.rangeFacet == 'free'){
          if(xaxis.rangeScroll == 'free'){
            var facetX = Array.from(new Set(data.filter(d => ((scroll.var != null)? (d[scroll.var] == vScroll): true) && d[facet.var] == vFacet).map(d => d[x.var.start])));
          }
          else{
            var facetX = Array.from(new Set(data.filter(d => d[facet.var] == vFacet).map(d => d[x.var.start])));
          }
        }
        else{
          if(xaxis.rangeScroll == 'free'){
            var facetX = Array.from(new Set(data.filter(d => ((scroll.var != null)? (d[scroll.var] == vScroll): true)).map(d => d[x.var.start])));
          }
          else{
            var facetX = Array.from(new Set(data.map(d => d[x.var.start])));
          }
        }

        facetX.sort(function(a, b) {
          return a - b;
        });

        if(x.order == 'alphabetical'){ facetX.sort(); }
        if(!x.ascending){ facetX.reverse(); }

        domainFacet[iScroll][iFacet] = {'facet': vFacet, 'x': facetX}
      })
    }
    else{

      if(xaxis.rangeScroll == 'free'){
        var facetX = Array.from(new Set(data.filter(d => ((scroll.var != null)? (d[scroll.var] == vScroll): true)).map(d => d[x.var.start])));
      }
      else{
        var facetX = Array.from(new Set(data.map(d => d[x.var.start])));
      }


      if(x.order == 'alphabetical'){ facetX.sort(); }
      if(!x.ascending){ facetX.reverse(); }

      domainFacet[iScroll][0] = {'facet': null, 'x': facetX}
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









  // ---------------->
  // ----- DATA ----->
  // ---------------->
  var dataPlot = [];

  domainScroll.forEach(function(vScroll, iScroll){
    dataPlot[iScroll] = []

    domainFacet[iScroll].forEach(function(vFacet, iFacet){
      dataPlot[iScroll][iFacet] = [];

      var minYvalue = (yaxis.range[0] != null)? yaxis.range[0]: d3.min(data, d => d[y.var]);
      if(yaxis.rangeScroll == 'fixed' && yaxis.rangeFacet == 'fixed'){
        var minYvalue = (yaxis.range[0] != null)? yaxis.range[0]: d3.min(data, d => d[y.var]);
        var maxYvalue = (yaxis.range[1] != null)? yaxis.range[1]: d3.max(data, d => d[y.var]);
      }
      else if(yaxis.rangeScroll == 'fixed' && yaxis.rangeFacet == 'free'){
        var minYvalue = (yaxis.range[0] != null)? yaxis.range[0]: d3.min(data.filter(d => ((scroll.var != null)? d[scroll.var] == vScroll: true)), d => d[y.var]);
        var maxYvalue = (yaxis.range[1] != null)? yaxis.range[1]: d3.max(data.filter(d => ((scroll.var != null)? d[scroll.var] == vScroll: true)), d => d[y.var]);
      }
      else if(yaxis.rangeScroll == 'free' && yaxis.rangeFacet == 'fixed'){
        var minYvalue = (yaxis.range[0] != null)? yaxis.range[0]: d3.min(data.filter(d => ((facet.var != null)? d[facet.var] == vFacet['facet']: true)), d => d[y.var]);
        var maxYvalue = (yaxis.range[1] != null)? yaxis.range[1]: d3.max(data.filter(d => ((facet.var != null)? d[facet.var] == vFacet['facet']: true)), d => d[y.var]);
      }
      else{
        var minYvalue = (yaxis.range[0] != null)? yaxis.range[0]: d3.min(data.filter(d => ((scroll.var != null)? d[scroll.var] == vScroll: true) && ((facet.var != null)? d[facet.var] == vFacet['facet']: true)), d => d[y.var]);
        var maxYvalue = (yaxis.range[1] != null)? yaxis.range[1]: d3.max(data.filter(d => ((scroll.var != null)? d[scroll.var] == vScroll: true) && ((facet.var != null)? d[facet.var] == vFacet['facet']: true)), d => d[y.var]);
      }

      domainSwitcher.forEach(function(vSwitcher, iSwitcher){
        dataPlot[iScroll][iFacet][iSwitcher] = [];

        vFacet['x'].forEach(function(vX, iX){

          var rectBottom = minYvalue;

          domainGroup.forEach(function(vGroup, iGroup){

            var dataObs = data.filter(d => ((scroll.var != null)? d[scroll.var] == vScroll: true) && ((facet.var != null)? d[facet.var] == vFacet['facet']: true) && ((switcher.var != null)? d[switcher.var] == vSwitcher: true) && ((group.var != null)? d[group.var] == vGroup['group']: true) && d[x.var.start] == vX )[0]

            // Color of bar
            var newObs_clr;
            if(group.var != null){
              newObs_clr = (dataObs)? domainGroup.map(d => d['color'])[iGroup]: 'white';
            }
            else{
              if(clr.var != null){
                newObs_clr = (dataObs)? dataObs[clr.var]:'white';
              }
              else{
                newObs_clr = (clr.value != null)? clr.value: '#e32726';
              }
            }

            var newObs = {
              'switcher': vSwitcher,
              'facet': (facet.var != null && dataObs)? dataObs[facet.var]: null,
              'group': (group.var != null)? vGroup['group']: null,
              'group_index': (group.var != null)? domainGroup.map(d => d['group']).indexOf(vGroup['group']): null,
              'clr': newObs_clr, //(clr.var != null)? ( (dataObs)? dataObs[clr.var]:'white') : ((clr.value != null)? clr.value: '#e32726'),
              'opacity': (opacity.var != null)? ( (dataObs)? dataObs[opacity.var]:1.0) : ((opacity.value != null)? opacity.value: 1.0),
              'y': (dataObs)? dataObs[y.var]: minYvalue,
              'x': vX,
              'x_end': (dataObs)? ((x.var.end != null)? dataObs[x.var.end]: dataObs[x.var.start]): vX,
              //'y_ci_l': (y.ci[0] != null && dataObs)? dataObs[y.ci[0]]: (dataObs)? dataObs[y.var]:0,
              //'y_ci_u': (y.ci[1] != null && dataObs)? dataObs[y.ci[1]]: (dataObs)? dataObs[y.var]:0,
              'rectTop': (minYvalue < 0)? (rectBottom + ((dataObs)? (dataObs[y.var] - minYvalue):0)): (rectBottom + ((dataObs)? dataObs[y.var]:0)),
              'rectBottom': rectBottom,
              'rectLeft': (dataObs)? dataObs[x.var.start]: vX,
              'rectRight': (dataObs)? ((x.var.end != null)? dataObs[x.var.end]: dataObs[x.var.start]): vX,
            }


            if(barmode == 'stack'){
              rectBottom += ((dataObs)? dataObs[y.var]:0)
            }


            if(bar.text != null){
              bar.text.forEach((v, i) => {
                  newObs[v['var']] = (dataObs)?dataObs[v['var']]: null
              });
            }

            if(tooltip_text != null){
              tooltip_text.forEach((v, i) => {
                  v['text'].forEach((v2, i2) => {
                    newObs[v2['var']] = (dataObs)?dataObs[v2['var']]: null
                  })
              });
            }

            if(hline.var != null){
              newObs[hline.var['name']] = (dataObs)?dataObs[hline.var['name']]: null
            }

            dataPlot[iScroll][iFacet][iSwitcher].push(newObs);

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

  if (canvas == undefined){
    var canvas = {width:960}
  }
  if(canvas.width == null){
    canvas.width = 960
  }

  var height = {
    //'bar': (bar != null)? ( ((((bar.size*1.1)*bar.text.length)+6)*100)/90 + bar.extra_height ) : ( (((bar.size*1.1)+6)*100)/90 + bar.extra_height )
  };



  // Title Height
  //height.title = 0;
  //if(title.value != null){
  //  height.title = margin.g + (title.size*1.1)*splitWrapText(title.value, (canvas.width - margin.left - margin.right), fontSize=title.size, fontWeight=title.weight, fontFamily=font.family).length;
  //}

  height.title = 0;
  var title_ypos = [];
  if(title.value != null){
    var totTitleHeight = 0
    title.value.forEach(function(vTitle, iTitle){
      title_ypos[iTitle] = height.title;

      height.title += (vTitle.size*1.1)*splitWrapText(vTitle.text, (canvas.width - margin.left - margin.right), fontSize=vTitle.size, fontWeight=vTitle.weight, fontFamily=font.family).length;
    })
    height.title += (margin.g);
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

  var legendValues = [];

  // Group legend items
  if(group.var != null ){
    if(group.show == undefined || group.show){
      domainGroup.map(d => d['group']).forEach(function(v,i){
        legendValues.push({
          'text': v,
          'type': 'rect'
        })
      })
    }
  }

  // Horizontal lines from Variable legend items
  if(hline.var != null && hline.var.label != null){
    legendValues.push({
      'text': hline.var.label,
      'type': 'line',
      'clr': hline.var.clr,
      'line_style': hline.var.line_style,
      'width': hline.var.width
    })
  }

  // Horizontal lines from values legend items
  if(hline.value != null && hline.value.filter(d => d['label'] != null).map(d => d['label']).length > 0){
    hline.value.filter(d => d['label'] != null).forEach(function(v, i){
      legendValues.push({
        'text': v.label,
        'type': 'line',
        'clr': v.clr,
        'line_style': v.line_style,
        'width': v.width
      })
    })
  }
  //console.log('legendValues:', legendValues)

  if(legendValues.length > 0){

    var legendText = splitWrapTextElement(legendValues.map(d => d['text']), width=canvas.width-(margin.left+margin.right), padding=10, extra_width=14+5, fSize=group.size, fWeight=group.weight, fFamily=font.family);

    // Get colors (and line properties, if needed)
    legendText.forEach(function(v, i){
      if(group.var != null && (group.show == undefined || group.show) && i < domainGroup.length){
        v['type'] = 'rect';
        v['color'] = domainGroup[i]['color']
      }
      else{
        v['type'] = legendValues[i]['type'];
        v['color'] = legendValues[i]['clr'];
        v['line_style'] = legendValues[i]['line_style'];
        v['width'] = legendValues[i]['width'];
      }
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
  else{
    var legendText = [];
  }




  // Y-Axis Label Margin
  margin.yaxisLabel = (yaxis.label.value != null)? (yaxis.label.size*1.1)*splitWrapText(yaxis.label.value, yaxis.height, fontSize=yaxis.label.size, fontWeight=yaxis.label.weight, fontFamily=font.family).length + (10) : 0;
  //console.log('margin.yaxisLabel', margin.yaxisLabel)






  // --- Margin at top of y-axis to leave room for text at end of bars --->
  margin.bar_text = 0;
  if(bar.text != null && (barmode == 'overlay' || barmode == 'group')){

    dataPlot.forEach(function(vScroll, iScroll){
      vScroll.forEach(function(vFacet, iFacet){
        vFacet.forEach(function(vSwitcher, iSwitcher){

            bar.text.forEach(function(vBarText, iBarText){

              var text_val_prefix = (vBarText['prefix'] != null)? vBarText['prefix']: '';
              var text_val_main = (vBarText['format'] != null)? d3.format(vBarText['format'])(vSwitcher[vBarText['var']]): vSwitcher[vBarText['var']];
              var text_val_suffix = (vBarText['suffix'] != null)? vBarText['suffix']: '';
              var text_val = text_val_prefix + text_val_main + text_val_suffix;


              //margin.bar_text = ( (textWidth(text_val, bar.size, bar.weight)+5) > margin.bar_text)? (textWidth(text_val, bar.size, bar.weight)+5): margin.bar_text;
              margin.bar_text = Math.max(margin.bar_text, textWidth(text_val, bar.size, bar.weight)+10);
            })

        })
      })
    })

  }





  // --- Y-Axis --->

  var yScale = [];
  var yAxisChart = [];
  margin.yaxis = 0;


  domainFacet.forEach(function(vScroll, iScroll){
    yScale[iScroll] = [];
    yAxisChart[iScroll] = [];

    vScroll.forEach(function(vFacet, iFacet){

      // Scale
      var minYvalue = Infinity;
      var maxYvalue = -Infinity;

      if(yaxis.rangeFacet == 'free' && yaxis.rangeScroll == 'free'){

          dataPlot[iScroll][iFacet].forEach(function(vSwitcherData, iSwitcherData){
            vSwitcherData.forEach(function(vData, iData){
              minYvalue = Math.min(minYvalue, vData['rectBottom']);
              maxYvalue = Math.max(maxYvalue, vData['rectTop']);
            })
          })

      }
      else if(yaxis.rangeFacet == 'free' && yaxis.rangeScroll == 'fixed'){

          dataPlot[iScroll].forEach(function(vFacetData, iFacetData){
            vFacetData.forEach(function(vSwitcherData, iSwitcherData){
              vSwitcherData.forEach(function(vData, iData){
                minYvalue = Math.min(minYvalue, vData['rectBottom']);
                maxYvalue = Math.max(maxYvalue, vData['rectTop']);
              })
            })
          })

      }
      else if(yaxis.rangeFacet == 'fixed' && yaxis.rangeScroll == 'free'){

        dataPlot.forEach(function(vScrollData, iScrollData){
          vScrollData[iFacet].forEach(function(vFacetData, iFacetData){
            vFacetData.forEach(function(vSwitcherData, iSwitcherData){
              vSwitcherData.forEach(function(vData, iData){
                minYvalue = Math.min(minYvalue, vData['rectBottom']);
                maxYvalue = Math.max(maxYvalue, vData['rectTop']);
              })
            })
          })
        })

      }
      else{

          dataPlot.forEach(function(vScrollData, iScrollData){
            vScrollData.forEach(function(vFacetData, iFacetData){
              vFacetData.forEach(function(vSwitcherData, iSwitcherData){
                vSwitcherData.forEach(function(vData, iData){
                  minYvalue = Math.min(minYvalue, vData['rectBottom']);
                  maxYvalue = Math.max(maxYvalue, vData['rectTop']);
                })
              })
            })
          })

      }


      var yScaleDomain = [
        (yaxis.range[1] != null)? yaxis.range[1]: maxYvalue,
        (yaxis.range[0] != null)? yaxis.range[0]: minYvalue
      ]
      if (!y.ascending){ yScaleDomain.reverse() }


      yScale[iScroll][iFacet] = d3.scaleLinear()
      .domain(yScaleDomain)
      .range([
        yaxis.offset.top + margin.bar_text,
        yaxis.height - yaxis.offset.bottom
      ]);



      // Axis
      yAxisChart[iScroll][iFacet] = d3.axisLeft(yScale[iScroll][iFacet])
      .tickFormat((d) => (yaxis.suffix != null)? (((yaxis.format) != null? d3.format(yaxis.format)(d): d) + yaxis.suffix): ((yaxis.format) != null? d3.format(yaxis.format)(d): d) );


      if(yaxis.num_ticks != null){
        yAxisChart[iScroll][iFacet].ticks(yaxis.num_ticks)
      }
      if(xaxis.show_grid){
        yAxisChart[iScroll][iFacet].tickSize(-(xaxis.offset.left + (xScale[iScroll][iFacet].range()[1] - xScale[iScroll][iFacet].range()[0])));
      }


      yAxisChart[iScroll][iFacet].scale().ticks().forEach(function(v, i){
        var tickval = (yaxis.suffix != null)? (((yaxis.format) != null? d3.format(yaxis.format)(v): v) + yaxis.suffix): ((yaxis.format) != null? d3.format(yaxis.format)(v): v)
        margin.yaxis = Math.max(margin.yaxis, textWidth(tickval, yaxis.tick.size, yaxis.tick.weight) + 9 )
      })
    })

  })
  //console.log('margin.yaxis', margin.yaxis)

  // <--- Y-Axis ---





  // --- X-Axis --->

  var xScale = [], xAxisChart = [], barShiftScale = [];
  height.xaxis = [];

  domainFacet.forEach(function(vScroll, iScroll){
    xScale[iScroll] = [];
    xAxisChart[iScroll] = [];
    barShiftScale[iScroll] = []
    height.xaxis[iScroll] = [];

    facetLengths = [];
    vScroll.forEach(function(vFacet, iFacet){
      facetLengths.push(vFacet['x'].length)
    })
    var maxFacetLength = facetLengths.reduce((a, b) => Math.max(a, b), -Infinity)
    var xWidth = (canvas.width - (margin.left + xaxis.offset.right + margin.right)) - (margin.yaxisLabel + margin.yaxis + xaxis.offset.left)


    vScroll.forEach(function(vFacet, iFacet){
      // Scale
      xScale[iScroll][iFacet] = d3.scaleBand()
        .domain(vFacet['x'])
        .range([
          (margin.yaxisLabel + margin.yaxis + xaxis.offset.left) + (xWidth*((1 - (vFacet['x'].length/maxFacetLength))*0.5)),
          margin.yaxisLabel + margin.yaxis + xaxis.offset.left + xWidth - (xWidth*((1 - (vFacet['x'].length/maxFacetLength))*0.5))
        ])
        .padding([0.01]);


      // Axis
      xAxisChart[iScroll][iFacet] = d3.axisBottom(xScale[iScroll][iFacet]);


      // Scale for shifting Bar Groups left/right on X-Axis bandwidth
      barShiftScale[iScroll][iFacet] = d3.scaleLinear()
      .domain([
        0,
        domainGroup.length-1
      ])
      .range([
        -((domainGroup.length-1)*(((xScale[iScroll][iFacet].bandwidth()*0.95)/domainGroup.length)/2)),
        (domainGroup.length-1)*(((xScale[iScroll][iFacet].bandwidth()*0.95)/domainGroup.length)/2)
      ]);

      //console.log('xScale', iScroll, iFacet, 'RANGE:', xScale[iScroll][iFacet].range(), 'DOMAIN:', xScale[iScroll][iFacet].domain())


      // Calculate maximum x-axis height for all facets within all scrolls
      if(xaxis.tick.orientation == 'v'){

        height.xaxis[iScroll][iFacet] = 20;

        vFacet['x'].forEach(function(vXtick, iXtick){

            splitWrapText(vXtick, width=xaxis.tick.splitWidth, fontSize=xaxis.tick.size, fontWeight=xaxis.tick.weight, fontFamily=font.family).forEach(function(vXtickSplit, iXtickSplit){
              height.xaxis[iScroll][iFacet] = Math.max(
                height.xaxis[iScroll][iFacet],
                20 + textWidth(vXtickSplit, fontSize=xaxis.tick.size, fontWeight=xaxis.tick.weight, fontFamily=font.family)
              )
            })

        })

      }
      else{

        height.xaxis[iScroll][iFacet] = 20;

        vFacet['x'].forEach(function(vXtick, iXtick){
            height.xaxis[iScroll][iFacet] = Math.max(
              height.xaxis[iScroll][iFacet],
              20 + ((xaxis.tick.size*1.1)*splitWrapText(vXtick, width=xScale[iScroll][iFacet].bandwidth()*0.95, fontSize=xaxis.tick.size, fontWeight=xaxis.tick.weight, fontFamily=font.family).length)
            )
        })

      }

      //console.log('height.xaxis[iScroll][iFacet]', height.xaxis[iScroll][iFacet])
    })
  })
  //console.log('height.xaxis', height.xaxis)

  // <--- X-Axis ---






  // --- Decide font-size for each observation based on width of bars --->

  dataPlot.forEach(function(vScroll, iScroll){
    vScroll.forEach(function(vFacet, iFacet){
      vFacet.forEach(function(vSwitcher, iSwitcher){
        vSwitcher.forEach(function(vObs, iObs){
          if(bar.text != null){
            if(barmode=='group'){
              vObs['font-size'] = ( ((bar.size*1.1)*bar.text.length) <= ( (bar.maxWidth != null)?Math.min(bar.maxWidth, ((xScale[iScroll][iFacet].bandwidth()*0.95)/domainGroup.length)*0.95) :((xScale[iScroll][iFacet].bandwidth()*0.95)/domainGroup.length)*0.95) )? bar.size: ((( (bar.maxWidth != null)?Math.min(bar.maxWidth, ((xScale[iScroll][iFacet].bandwidth()*0.95)/domainGroup.length)*0.95) :((xScale[iScroll][iFacet].bandwidth()*0.95)/domainGroup.length)*0.95 )/bar.text.length)/1.1)
            }
            else{
              vObs['font-size'] = ( ((bar.size*1.1)*bar.text.length) <= ( (bar.maxWidth != null)?Math.min(bar.maxWidth, xScale[iScroll][iFacet].bandwidth()*0.95):xScale[iScroll][iFacet].bandwidth()*0.95 ) )? bar.size: ((( (bar.maxWidth != null)?Math.min(bar.maxWidth, xScale[iScroll][iFacet].bandwidth()*0.95) :xScale[iScroll][iFacet].bandwidth()*0.95 )/bar.text.length)/1.1)
            }

            //vObs['font-size'] = ( ((bar.size*1.1)*bar.text.length) <= (xScale[iScroll][iFacet](vObs['rectRight']) - xScale[iScroll][iFacet](vObs['rectLeft'])) )? bar.size: (((xScale[iScroll][iFacet](vObs['rectRight']) - xScale[iScroll][iFacet](vObs['rectLeft']))/bar.text.length)/1.1)
          }
          else{
            vObs['font-size'] = 0;
          }
        })
      })
    })
  });
  //console.log('dataPlot:', dataPlot)
  // <--- Decide font-size for each observation based on width of bars ---




  // X-Axis Label Height
  height.xaxisLabel = (xaxis.label.value != null)? (xaxis.label.size*1.1)*splitWrapText(xaxis.label.value, canvas.width - (margin.left + margin.yaxisLabel + margin.yaxis + margin.right), fontSize=xaxis.label.size, fontWeight=xaxis.label.weight, fontFamily=font.family).length + (10) : 0;








  // Total Height of all Facet Labels and y-Positions of Facets
  var facet_ypos = [];
  height.facetLabel = [];
  height.facet = [];

  domainFacet.forEach(function(vScroll, iScroll){

    facet_ypos[iScroll] = [];
    height.facetLabel[iScroll] = [];
    height.facet[iScroll] = 0;

    var facetPos = 0;

    vScroll.forEach(function(vFacet, iFacet){
      var numFacetLabelLines = (vFacet['facet'] != null)? splitWrapText(vFacet['facet'], (canvas.width - margin.left - margin.right), fontSize=facet.size, fontWeight=facet.weight, fontFamily=font.family).length: 0;
      height.facetLabel[iScroll][iFacet] = (numFacetLabelLines*(facet.size*1.1)) + ((facet.var != null)? facet.space_above_title: 0);

      facet_ypos[iScroll][iFacet] = facetPos + height.facetLabel[iScroll][iFacet];

      facetPos += height.facetLabel[iScroll][iFacet] + yaxis.offset.top + yaxis.height + yaxis.offset.bottom + height.xaxis[iScroll][iFacet];

    })

    height.facet[iScroll] += d3.sum(height.facetLabel[iScroll]);
  })
  //console.log('height.facet:', height.facet)
  //console.log('height.facetLabel:', height.facetLabel)
  //console.log('facet_ypos:', facet_ypos)





  var maxFacets = 0
  domainFacet.forEach(function(vScroll, iScroll){
    maxFacets = Math.max(maxFacets, vScroll.length)
  })

  height.yaxis = (yaxis.height*maxFacets);





  // Calculate height of each Scroll
  height.scrollFace = []
  height.facet.forEach(function(vScroll, iScroll){

    // Height of FACET LABELS + ((yaxis.offset.top + yaxis.height + yaxis.offset.bottom)*No. Facets) + d3.sum(x-axis heights)
    height.scrollFace[iScroll] = d3.sum(height.facetLabel[iScroll]) + (yaxis.height*height.facetLabel[iScroll].length) + vScroll + d3.sum(height.xaxis[iScroll])

  })
  //console.log('height.scrollFace:', height.scrollFace)



  // Canvas Height
  var canvas_height = margin.top + height.title + height.scroll + height.switcher + height.legend + d3.max(height.scrollFace) + height.xaxisLabel + margin.bottom;

  /*console.log('margin.top', margin.top)
  console.log('height.title', height.title)
  console.log('height.scroll', height.scroll)
  console.log('height.switcher', height.switcher)
  console.log('height.legend', height.legend)
  console.log('d3.max(height.scrollFace)', d3.max(height.scrollFace))
  console.log('margin.bottom', margin.bottom)
  console.log('canvas_height', canvas_height)*/


  // <------------------------
  // <----- Graph Sizing -----
  // <------------------------











  // ----- Change height of parent DIV ----->
  /*d3.select(html_id)
    .style('height', (canvas_height + 10) + 'px') ;*/

  // ----- Create SVG element ----->
  var svg = d3.select(html_id)
      .append("div")
      .classed("svg-container", true)
      .append("svg")
      .attr("preserveAspectRatio", "xMinYMin meet")
      .attr("viewBox", "0 0 " + canvas.width + " " + canvas_height)
      .classed("svg-content", true)
      .append('g');

      /*d3.select(html_id)
      .append("svg")
      .attr('width', canvas.width)
      .attr('height', canvas_height)
      //.attr("viewBox", [-canvas.width/2, -canvas_height/2, canvas.width, canvas_height])
      //.attr("style", "max-width: 100%; height: auto; height: intrinsic;");*/



  // Reference lines
  /*
  svg.selectAll('ref_lines')
  .data([
    0,
    margin.top,
    margin.top + height.title,
    margin.top + height.title + height.scroll,
    margin.top + height.title + height.scroll + height.switcher,
    margin.top + height.title + height.scroll + height.switcher + height.legend,
    margin.top + height.title + height.scroll + height.switcher + height.legend + d3.max(height.scrollFace),
    margin.top + height.title + height.scroll + height.switcher + height.legend + d3.max(height.scrollFace) + height.xaxisLabel,
    margin.top + height.title + height.scroll + height.switcher + height.legend + d3.max(height.scrollFace) + height.xaxisLabel + margin.bottom
  ])
  .enter()
  .append('path')
  .attr('d', d => 'M' + 10 + ',' + d + 'L' + (canvas.width - (margin.left + margin.right)) + ',' + d)
  .attr('stroke', 'red')
  .attr('stroke-width', '1');
  */



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
            .on('mouseover', function(d) {
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
            .on('mouseover', function(d) {
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
          .on('mouseover', function(d) {
              d3.select(this).style("cursor", "pointer");
          });


    switcherGroup.append('rect')
      .attr('class', function(d, i){ return 'switcher_' + i})
      .attr('width-value', d => d['width-value'])
      //.attr('x', d => 0 - (d['width-value']/2))
      //.attr('x', -5)
      .attr('x', 5)
      .attr('y', -3)
      .attr('width', d => d['width-value']-8)
      .attr('height', d => (d['text'].length*(switcher.size*1.1)) + 6)
      .attr('fill', '#d3d2d2');


    switcherGroup.append('text')
      .attr('class', function(d, i){ return 'switcher_' + i})
      .style('font-family', font.family)
      .style('font-size', switcher.size +  'px')
      .style('font-weight', switcher.weight)
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

      // --- Legend with Colored Rectangles --->
      var legend_rect = g_legend.selectAll('.legend')
        .data(legendText.filter(d => d['type'] == 'rect'))
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


      legend_rect.append('rect')
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

      legend_rect.append('text')
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


    if(legendText.length > 0 && legendText.filter(d => d['type'] == 'line').length > 0){

        // --- Legend with Lines --->
        var legend_line = g_legend.selectAll('.legend_line')
          .data(legendText.filter(d => d['type'] == 'line'))
          .enter()
          .append('g')
            .attr('class', function(d, i){ return "legend_line_" + i})
            .attr('transform', function(d){ return `translate(${d['x']}, ${(d['y'] + height.legendLabel)})` })
            .attr('opacity', 1.0);


        legend_line.append('path')
          .attr('class', function(d, i){ return "legend_" + i})
          .attr('x', 0)
          .style('stroke-dasharray', function(d){
            if(d['line_style'] == 'dashed'){ return '5' }
            else if(d['line_style'] == 'dotted'){ return '2' }
            else{ return '0' }
          })
          .attr('stroke', d => d['color'])
          .attr('stroke-width', d => d['width'])
          .attr('d', 'M ' + 0 + ',' + group.size*0.5 + ' L ' + group.size + ',' + group.size*0.5 + ' Z');


        legend_line.append('text')
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




      /*
      // --- Add Y-Axis Label to plot --->
      if(yaxis.label.value != null){
          g_scroll.append('text')
            .attr('class', 'yAxisLabel')
            .style('font-family', font.family)
            .style('font-size', yaxis.label.size + 'px')
            .style('font-weight', yaxis.label.weight)
            .style('text-anchor', 'middle')
            .style('dominant-baseline', 'hanging')
            .attr('x', -(yScale[iScroll][iFacet].range()[0] + ((yScale[iScroll][iFacet].range()[1] - yScale[iScroll][iFacet].range()[0])*0.5)) ) // Moves vertically (due to rotation)
            //.attr('x', -(height.scrollFace[iScroll]*0.5) ) // Moves vertically (due to rotation)
            .attr('y', 0) // Moves horizontally (due to rotation)
            .attr('transform', 'rotate(-90)')
            .text(yaxis.label.value)
            //.call(splitWrapTextSpan, height.yaxis0[iScroll], yaxis.label.size, yaxis.label.weight, font.family, valign='bottom', dy_extra=0);
            .call(splitWrapTextSpan, height.yaxis, yaxis.label.size, yaxis.label.weight, font.family, valign='bottom', dy_extra=0);
      }
      // <--- Add Y-Axis Label to plot ---
      */





      vScroll.forEach(function(vFacet, iFacet){


        var g_facet = g_scroll.append('g')
          .attr('class', 'facet_' + iFacet)
          .attr('transform', `translate(${0}, ${facet_ypos[iScroll][iFacet]})`)





        // --- Add line above Facet --->
        if(facet.line.show){
          g_facet.append('path')
            .attr('d', 'M' + margin.yaxisLabel + ',' + (-height.facetLabel[iScroll][iFacet] + (facet.space_above_title/2)) + 'L' + (canvas.width - (margin.left + margin.right)) + ',' + (-height.facetLabel[iScroll][iFacet] + (facet.space_above_title/2)))
            .attr('stroke', (facet.line.color != null)? facet.line.color: 'black')
            .attr('stroke-width', '2')
        }
        // <--- Add line above Facet ---





        // --- Facet Title --->
        if(facet.var != null){

          g_facet.selectAll('facet_text')
              .data(splitWrapText(domainFacet[iScroll][iFacet]['facet'], (canvas.width - margin.left - margin.yaxisLabel - margin.right), fontSize=facet.size, fontWeight=facet.weight, fontFamily=font.family))
              .enter()
              .append('text')
                .style('font-family', font.family)
                .style('font-size', facet.size +  'px')
                .style('font-weight', facet.weight)
                .style('text-anchor', 'middle')
                .style('dominant-baseline', 'hanging')
                .attr('class', "facet_text")
                .attr('x', margin.yaxisLabel + ((canvas.width - margin.left - margin.yaxisLabel - margin.right)/2))
                .attr('dy', function(d, i){ return i*1.1 + 'em'})
                .attr('transform', `translate(${0}, ${-height.facetLabel[iScroll][iFacet] + facet.space_above_title})`)
                .text(d => d);

        }
        // <--- Facet Title ---





        // --- Add Y-Axis Label to plot --->
        if(yaxis.label.value != null){
            g_scroll.append('text')
              .attr('class', 'yAxisLabel')
              .style('font-family', font.family)
              .style('font-size', yaxis.label.size + 'px')
              .style('font-weight', yaxis.label.weight)
              .style('text-anchor', 'middle')
              .style('dominant-baseline', 'hanging')
              .attr('x', -(yScale[iScroll][iFacet].range()[0] + ((yScale[iScroll][iFacet].range()[1] - yScale[iScroll][iFacet].range()[0])*0.5)) ) // Moves vertically (due to rotation)
              //.attr('x', -(height.scrollFace[iScroll]*0.5) ) // Moves vertically (due to rotation)
              .attr('y', 0) // Moves horizontally (due to rotation)
              .attr('transform', 'rotate(-90)')
              .text(yaxis.label.value)
              //.call(splitWrapTextSpan, height.yaxis0[iScroll], yaxis.label.size, yaxis.label.weight, font.family, valign='bottom', dy_extra=0);
              .call(splitWrapTextSpan, height.yaxis, yaxis.label.size, yaxis.label.weight, font.family, valign='bottom', dy_extra=0);
        }
        // <--- Add Y-Axis Label to plot ---





        // ----- Add Y-Axis to plot ----->
        if(yaxis.show){

          if(yaxis.show_grid){

            var maxXrange = xScale[iScroll][iFacet].range()[1] - xScale[iScroll][iFacet].range()[0];
            yAxisChart[iScroll][iFacet].tickSize(-(maxXrange + xaxis.offset.left));

          }

          var y_axis_chart = g_facet.append('g')
              .attr('class', "y_axis")
              .style('font-size', yaxis.tick.size + 'px')
              .attr('transform', "translate(" + (margin.yaxisLabel+margin.yaxis) + "," + 0 + ")")
              .call(yAxisChart[iScroll][iFacet]);


          y_axis_chart.selectAll(".tick text")
              .attr("y", '0.0')
              .call(splitWrapTextSpan, ((canvas.width*0.4) - (margin.left + margin.yaxisLabel)), yaxis.tick.size, yaxis.tick.weight, font.family, valign='center', dy_extra=0.32);

          // Remove Axis Line
          if(!yaxis.show_line){
            y_axis_chart.select(".domain").remove();
          }

          // Remove Axis Ticks
          if(!yaxis.show_ticks){
            y_axis_chart.selectAll(".tick").selectAll("line").remove();
          }

          if(yaxis.show_grid){
            y_axis_chart.selectAll(".tick line").attr('stroke', "#d3d2d2");
          }

        }
        // <----- Add Y-Axis to plot -----




        // ----- Add X-Axis to plot ----->

        if(xaxis.show){
          var x_axis_chart = g_facet.append('g')
              .attr('class', "x_axis_" + iFacet)
              .style('font-size', xaxis.tick.size + "px")
              .attr('transform', "translate(" + 0 + "," + yaxis.height + ")")
              .call(xAxisChart[iScroll][iFacet]);


          x_axis_chart.selectAll(".tick text")
              .attr('x', '0.0')
              .call(splitWrapTextSpan, (xaxis.tick.orientation == 'h')? xScale[iScroll][iFacet].bandwidth()*0.95: xaxis.tick.splitWidth, xaxis.tick.size, xaxis.tick.weight, font.family, valign='bottom', dy_extra=0.7);


          // --- Tick rotation --->
          if(xaxis.tick.orientation == 'v'){

            x_axis_chart.selectAll('text')
            .style('text-anchor', 'end')
            .attr("transform", 'rotate(-90)');


            x_axis_chart.selectAll('text').selectAll('tspan')
            .style('dominant-baseline', 'middle')
            .attr('dx', "-.8em")



            x_axis_chart.selectAll('text').selectAll('tspan').each((d,i,nodes) => {
                nodes[i].setAttribute('dy', parseFloat(nodes[i].getAttribute('dy')) - (0.55 + ((1.1*nodes.length)/2)) + 'em');
                //nodes[i].setAttribute('dy', '-0.5em');
            });


          }
          // <--- Tick rotation ---


          // Remove Axis Line
          if(!xaxis.show_line){
            x_axis_chart.select(".domain").remove();
          }


          // Remove Axis Ticks
          if(!xaxis.show_ticks){
            x_axis_chart.selectAll(".tick").selectAll("line").remove();
          }
        }
        // <----- Add X-Axis to plot -----






        // ----- Add X-Axis Label to plot ----->
        if(xaxis.label.value != null && (iFacet+1) == domainFacet[iScroll].length){
            g_facet.append('text')
              .attr('class', 'xaxis_label')
              .style('font-family', font.family)
              .style('font-size', xaxis.label.size + 'px')
              .style('font-weight', xaxis.label.weight)
              .style('text-anchor', 'middle')
              .style('dominant-baseline', 'hanging')
              .attr('x', xScale[iScroll][0].range()[0] + ((xScale[iScroll][0].range()[1] - xScale[iScroll][0].range()[0])*0.5) )
              .attr('y', yaxis.height + height.xaxis[iScroll][iFacet] )
              .text(xaxis.label.value)
              .call(splitWrapTextSpan, (xScale[iScroll][0].range()[1] - xScale[iScroll][0].range()[0]), xaxis.label.size, xaxis.label.weight, font.family, valign='bottom', dy_extra=0);
        }
        // <----- Add X-Axis Label to plot -----





        // ----- Add Bars, CI and Text to plot ----->
        vFacet[0].forEach(function(vSwitcher, iSwitcher){

            var g_data = g_facet.selectAll('.bar_rect')
              .data(vFacet[0])
              .enter()
              .append('g')
                .attr('class', function(d, i){
                  return 'scroll_' + iScroll +
                  ' switcher_0' +
                  ' facet_' + iFacet +
                  ' group_' + domainGroup.map(d => d['group']).indexOf(d['group']) +
                  ' obs_' + iScroll + '_0_' + iFacet + '_' + domainGroup.map(d => d['group']).indexOf(d['group']) + '_' + i +
                  ' bar'
                })
                .attr('rectTop', d => yScale[iScroll][iFacet](d['rectTop']))
                .attr('rectBottom', d => yScale[iScroll][iFacet](d['rectBottom']))
                .attr('rectLeft', d => xScale[iScroll][iFacet](d['rectLeft']) )
                .attr('rectRight', d => xScale[iScroll][iFacet](d['rectRight']) )
                .attr('rectWidth', d => xScale[iScroll][iFacet](d['rectRight']) - xScale[iScroll][iFacet](d['rectLeft']))
                .attr('rectHeight', d => yScale[iScroll][iFacet](d['rectTop']) - yScale[iScroll][iFacet](d['rectBottom']))
                .attr('color-value', function(d){
                   if(clr.var != null){ return d['clr'] }
                   else if(clr.value != null){ return clr.value }
                   else{ return '#e32726' }
                 })
                .attr('group-value', function(d){
                  if(group.var != null){ return d['group'] }
                  else{ return null }
                })
                //.attr('x-value', d => d['x'])
                .attr('x-value',  function(d, i){
                  if(barmode == 'group'){
                    return xScale[iScroll][iFacet](d['x']) + (xScale[iScroll][iFacet].bandwidth()/2) + barShiftScale[iScroll][iFacet](domainGroup.map(d => d['group']).indexOf(d['group']))
                  }
                  else{
                    //return xScale[iScroll][iFacet](d['rectLeft']) + (xScale[iScroll][iFacet].bandwidth()/2) - ((xScale[iScroll][iFacet].bandwidth()*0.95)/2)
                    return xScale[iScroll][iFacet](d['x'])
                  }
                })
                .attr('y-value', d => d['y'])
                .attr('opacity', 1.0)
                .attr('visibility', 'visible')
                .on('mouseover', (event, d) => {

                    if(event.currentTarget.getAttribute('visibility') == 'visible'){

                          // --- Tooltip --->
                          //var thisX = +event.currentTarget.getAttribute('rectLeft') + (+event.currentTarget.getAttribute('rectWidth')/2) + margin.left;
                          var thisX = +event.currentTarget.getAttribute('x-value') + margin.left;
                          var thisY = +event.currentTarget.getAttribute('rectTop') + (margin.top + height.title + height.scroll + height.switcher + height.legend);


                          var maxTextWidth = 0;
                          var rectHeight = 0;
                          var hoverText = [];


                          if(tooltip_text != null){
                            var scrollIndex = event.currentTarget.getAttribute('class').split(' ')[0].split('_')[1]
                            var facetIndex = event.currentTarget.getAttribute('class').split(' ')[2].split('_')[1]
                            var switcherIndex = event.currentTarget.getAttribute('class').split(' ')[1].split('_')[1]
                            var obsIndex = event.currentTarget.getAttribute('class').split(' ')[4].split('_')[5]

                            thisX += (barmode == 'group')? (((xScale[scrollIndex][facetIndex].bandwidth()*0.95)/domainGroup.length)*0.95)/2: (xScale[scrollIndex][facetIndex].bandwidth()*0.95)/2;
                            thisY += facet_ypos[scrollIndex][facetIndex];

                            var dataPoint = dataPlot[scrollIndex][facetIndex][switcherIndex][obsIndex]

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

                            rectHeight += (yaxis.tick.size*1.1);
                            maxTextWidth = (textWidth(event.currentTarget.getAttribute('x-value'), yaxis.tick.size, yaxis.tick.weight) > maxTextWidth)? textWidth(event.currentTarget.getAttribute('x-value'), yaxis.tick.size, yaxis.tick.weight): maxTextWidth;
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
                .on('mouseout', (event, v) => {
                        g_tooltip.style('opacity', 0).attr('transform', "translate(" + 0 + "," + 0 +")");
                });



            // --- Add Bars --->
            g_data.append('rect')
                .attr('class', function(d){
                  return 'bar_rect group_' + domainGroup.map(d => d['group']).indexOf(d['group'])
                })
                .attr('fill', function(d){ return d['clr'] })
                .attr('stroke-width', 1)
                .attr('stroke', function(d){
                  if(d['clr'] == 'white' || d['clr'] == 'rgb(255,255,255)' || d['clr'] == '#fff' || d['clr'] == '#ffffff'){
                    return '#d3d2d2'
                  }
                  else{
                    return d['clr']
                  }
                })
                //.attr('x-value', d => d['x'])
                .attr('x-value',  function(d, i){
                  if(barmode == 'group'){
                    return xScale[iScroll][iFacet](d['x']) + (xScale[iScroll][iFacet].bandwidth()/2) - ( (bar.maxWidth != null)? Math.min((bar.maxWidth)/2, ((xScale[iScroll][iFacet].bandwidth()*0.95)/domainGroup.length)/2): (((xScale[iScroll][iFacet].bandwidth()*0.95)/domainGroup.length)/2) ) + barShiftScale[iScroll][iFacet](domainGroup.map(d => d['group']).indexOf(d['group']))
                  }
                  else{
                    //return xScale[iScroll][iFacet](d['rectLeft']) + (xScale[iScroll][iFacet].bandwidth()/2) - ((xScale[iScroll][iFacet].bandwidth()*0.95)/2)
                    return xScale[iScroll][iFacet](d['x'])
                  }
                })
                .attr('y-value', d => d['y'])
                //.attr('x', d => xScale[iScroll][iFacet](d['rectLeft']) )
                .attr('x', function(d, i){
                  if(barmode == 'group'){
                    return xScale[iScroll][iFacet](d['x']) + (xScale[iScroll][iFacet].bandwidth()/2) - ( (bar.maxWidth != null)? Math.min((bar.maxWidth)/2, ((xScale[iScroll][iFacet].bandwidth()*0.95)/domainGroup.length)/2): (((xScale[iScroll][iFacet].bandwidth()*0.95)/domainGroup.length)/2) ) + barShiftScale[iScroll][iFacet](domainGroup.map(p => p['group']).indexOf(d['group']))
                  }
                  else{
                    //return xScale[iScroll][iFacet](d['rectLeft']) + (xScale[iScroll][iFacet].bandwidth()/2) - ((xScale[iScroll][iFacet].bandwidth()*0.95)/2)
                    return xScale[iScroll][iFacet](d['x']) + (xScale[iScroll][iFacet].bandwidth()/2) - ( (bar.maxWidth != null)? Math.min((bar.maxWidth)/2, ((xScale[iScroll][iFacet].bandwidth()*0.95)/domainGroup.length)/2): (((xScale[iScroll][iFacet].bandwidth()*0.95)/domainGroup.length)/2) )
                  }
                })
                .attr('y', d => yScale[iScroll][iFacet](d['rectBottom']) ) //yScale[iScroll][iFacet].range()[1] )
                //.attr('width', d => xScale[iScroll][iFacet](d['rectRight']) - xScale[iScroll][iFacet](d['rectLeft']))
                .attr('width', function(d, i){
                  if(barmode == 'group'){
                    return (bar.maxWidth != null)? Math.min( ((xScale[iScroll][iFacet].bandwidth()*0.95)/domainGroup.length)*0.95, bar.maxWidth): ((xScale[iScroll][iFacet].bandwidth()*0.95)/domainGroup.length)*0.95
                  }
                  else{
                    return (bar.maxWidth != null)? Math.min( xScale[iScroll][iFacet].bandwidth()*0.95, bar.maxWidth): xScale[iScroll][iFacet].bandwidth()*0.95
                  }
                })
                .attr('height', 0)
                .attr('opacity', d => d['opacity'])
                .attr('visibility', 'visible')
                .transition()
                //.delay(d => (domainX.indexOf(d['x'])/domainX.length)*800)
                .duration(800)
                  .attr('y', d => yScale[iScroll][iFacet](d['rectTop']) )
                  .attr('height', function(d) { return yScale[iScroll][iFacet](d['rectBottom']) - yScale[iScroll][iFacet](d['rectTop']) });

            // <--- Add Bars ---




            // --- Add CI --->
            /*
            if(x.ci[0] != null && x.ci[1] != null){
                g_data.append('path')
                    .attr('class', function(d){
                      return 'bar_ci group_' + domainGroup.map(d => d['group']).indexOf(d['group'])
                    })
                    .attr('stroke', 'black')
                    .attr('x-value', d => d['x'])
                    .attr('cil-value', d => (x.ci[0] != null)? d['x_ci_l']: d['x'])
                    .attr('ciu-value', d => (x.ci[1] != null)? d['x_ci_u']: d['x'])
                    .attr('d', d =>
                    'M' + xScale[iScroll][iFacet](d['x_ci_l']) + ',' + (yScale[iScroll][iFacet](d['y']) + (xScale[iScroll][iFacet].bandwidth()/2) + (barShiftScale(domainGroup.map(d => d['group']).indexOf(d['group']))) - 3) + 'L' +  xScale[iScroll][iFacet](d['x_ci_l']) + ',' + (yScale[iScroll][iFacet](d['y']) + (xScale[iScroll][iFacet].bandwidth()/2) + (barShiftScale(domainGroup.map(d => d['group']).indexOf(d['group']))) + 3)  +
                    'M' + xScale[iScroll][iFacet](d['x_ci_l']) + ',' + (yScale[iScroll][iFacet](d['y']) + (xScale[iScroll][iFacet].bandwidth()/2) + (barShiftScale(domainGroup.map(d => d['group']).indexOf(d['group'])))) + 'L' +  xScale[iScroll][iFacet](d['x_ci_u']) + ',' + (yScale[iScroll][iFacet](d['y']) + (xScale[iScroll][iFacet].bandwidth()/2) + (barShiftScale(domainGroup.map(d => d['group']).indexOf(d['group'])))) +
                    'M' + xScale[iScroll][iFacet](d['x_ci_u']) + ',' + (yScale[iScroll][iFacet](d['y']) + (xScale[iScroll][iFacet].bandwidth()/2) + (barShiftScale(domainGroup.map(d => d['group']).indexOf(d['group']))) - 3) + 'L' +  xScale[iScroll][iFacet](d['x_ci_u']) + ',' + (yScale[iScroll][iFacet](d['y']) + (xScale[iScroll][iFacet].bandwidth()/2) + (barShiftScale(domainGroup.map(d => d['group']).indexOf(d['group']))) + 3) +
                    'M' + xScale[iScroll][iFacet](d['x']) + ',' + (yScale[iScroll][iFacet](d['y']) + (xScale[iScroll][iFacet].bandwidth()/2) + (barShiftScale(domainGroup.map(d => d['group']).indexOf(d['group']))) - 5) + 'L' +  xScale[iScroll][iFacet](d['x']) + ',' + (yScale[iScroll][iFacet](d['y']) + (xScale[iScroll][iFacet].bandwidth()/2) + (barShiftScale(domainGroup.map(d => d['group']).indexOf(d['group']))) + 5)
                    )
                    .attr('opacity', 1.0)
                    .attr('visibility', 'visible');

            }
            */
            // <--- Add CI ---




            // --- Add text to bars --->
            if(bar.text != null){

                var g_bar_text = g_data.append('text')
                      .attr('class', function(d){
                        return 'bar_text group_' + domainGroup.map(d => d['group']).indexOf(d['group'])
                      })
                      /*.style('fill', function(d){
                        if(barmode=='stack'){
                          if(lightOrDark(d['clr']) == 'light'){ return 'black'}
                          else{ return 'white' }
                        }
                        else{ return 'black' }
                      })*/
                      .style('fill', function(d){
                        if(barmode=='stack'){
                          if(lightOrDark(d['clr']) == 'light'){ return 'black'}
                          else{ return 'white' }
                        }
                        else{
                          if(d['clr'] == 'white' || d['clr'] == 'rgb(255,255,255)' || d['clr'] == '#fff' || d['clr'] == '#ffffff'){
                            return '#d3d2d2'
                          }
                          else{
                            return d['clr']
                          }
                        }
                      })
                      .style('font-family', font.family)
                      //.style('font-size', bar.size + 'px')
                      .style('font-size', function(d){
                        if(barmode=='group'){
                          if( ((bar.size*1.1)*bar.text.length) <= ( (bar.maxWidth != null)? Math.min(bar.maxWidth, ((xScale[iScroll][iFacet].bandwidth()*0.95)/domainGroup.length)*0.95): ((xScale[iScroll][iFacet].bandwidth()*0.95)/domainGroup.length)*0.95 ) ){
                            return bar.size + 'px'
                          }
                          else{
                            return (( (bar.maxWidth != null)? Math.min(bar.maxWidth, ((xScale[iScroll][iFacet].bandwidth()*0.95)/domainGroup.length)*0.95): ((xScale[iScroll][iFacet].bandwidth()*0.95)/domainGroup.length)*0.95 )/bar.text.length)/1.1 + 'px'
                          }
                        }
                        else{
                          if( ((bar.size*1.1)*bar.text.length) <= ( (bar.maxWidth != null)? Math.min(bar.maxWidth, xScale[iScroll][iFacet].bandwidth()*0.95): xScale[iScroll][iFacet].bandwidth()*0.95 ) ){
                            return bar.size + 'px'
                          }
                          else{
                            return ( ( (bar.maxWidth != null)? Math.min(bar.maxWidth, xScale[iScroll][iFacet].bandwidth()*0.95): xScale[iScroll][iFacet].bandwidth()*0.95)/bar.text.length )/1.1 + 'px'
                          }
                        }
                      })
                      .style('font-weight', bar.weight)
                      .style('text-anchor', (barmode == 'overlay' || barmode == 'group')? 'start': 'middle')
                      .style('dominant-baseline', 'hanging')
                      //.attr('cil-value', d => (x.ci[0] != null)? d['x_ci_l']: d['x'])
                      //.attr('ciu-value', d => (x.ci[1] != null)? d['x_ci_u']: d['x'])
                      .attr('opacity', 0.0)
                      .attr('visibility', 'visible')
                      //.attr('x', d => xScale[iScroll][iFacet](d['x']) + ((xScale[iScroll][iFacet](d['rectRight']) - xScale[iScroll][iFacet](d['rectLeft']))/2) )
                      .attr('x', function(d, i){
                        if(barmode == 'group'){
                          return xScale[iScroll][iFacet](d['x']) + (xScale[iScroll][iFacet].bandwidth()/2) + barShiftScale[iScroll][iFacet](domainGroup.map(p => p['group']).indexOf(d['group']))
                        }
                        else{
                          //return xScale[iScroll][iFacet](d['rectLeft']) + (xScale[iScroll][iFacet].bandwidth()/2) - ((xScale[iScroll][iFacet].bandwidth()*0.95)/2)
                          return xScale[iScroll][iFacet](d['x']) + (xScale[iScroll][iFacet].bandwidth()/2)
                        }
                      })
                      //.attr('y', d => (barmode == 'overlay')? yScale[iScroll][iFacet](d['rectBottom'])+5: yScale[iScroll][iFacet](d['rectBottom']) )
                      .attr('y', function(d, i){
                         if(barmode == 'group'){
                           return yScale[iScroll][iFacet](d['rectTop'])-5
                         }
                         else if(barmode == 'overlay'){
                           return yScale[iScroll][iFacet](d['rectTop'])-5
                         }
                         else{
                           return yScale[iScroll][iFacet](d['rectTop']) + ((yScale[iScroll][iFacet](d['rectBottom']) - yScale[iScroll][iFacet](d['rectTop']))/2)
                         }
                      })
                      /*.attr('transform', function(d){
                           if(barmode == 'overlay'){
                             return `rotate(-90, ${xScale[iScroll][iFacet](d['rectLeft']) + ((xScale[iScroll][iFacet](d['rectRight']) - xScale[iScroll][iFacet](d['rectLeft']))/2)}, ${yScale[iScroll][iFacet](d['rectBottom'])+5})`
                           }
                           else{
                             return `rotate(-90, ${xScale[iScroll][iFacet](d['rectLeft']) + ((xScale[iScroll][iFacet](d['rectRight']) - xScale[iScroll][iFacet](d['rectLeft']))/2)}, ${yScale[iScroll][iFacet](d['rectBottom'])})`
                           }

                        })*/
                        .attr('transform', function(d){
                         if(barmode=='group'){
                            return `rotate(-90, ${xScale[iScroll][iFacet](d['x']) + (xScale[iScroll][iFacet].bandwidth()/2) + barShiftScale[iScroll][iFacet](domainGroup.map(p => p['group']).indexOf(d['group']))}, ${yScale[iScroll][iFacet](d['rectTop'])-5})`
                         }
                         else if(barmode=='overlay'){
                           return `rotate(-90, ${xScale[iScroll][iFacet](d['x']) + (xScale[iScroll][iFacet].bandwidth()/2)}, ${yScale[iScroll][iFacet](d['rectTop'])-5})`
                         }
                         else{
                           return `rotate(-90, ${xScale[iScroll][iFacet](d['x']) + (xScale[iScroll][iFacet].bandwidth()/2)}, ${yScale[iScroll][iFacet](d['rectTop']) + ((yScale[iScroll][iFacet](d['rectBottom']) - yScale[iScroll][iFacet](d['rectTop']))/2)})`
                         }
                       })
                      .each(d => d)
                      .call(barText, iScroll, iFacet);



                svg.select('.g_scroll_' + iScroll).selectAll('.facet_' + iFacet).selectAll('.bar_text') //.selectAll('tspan')
                  .transition()
                  //.delay(d => (domainX.indexOf(d['x'])*50)+800 )
                  //.delay(d => ((domainX.indexOf(d['x'])/domainX.length)*2000)+800)
                  .delay(800)
                  .duration(200)
                  //.attr('y', d => yScale[iScroll][iFacet](d['rectTop']) );
                  //.attr('x', d => xScale[iScroll][iFacet](d['rectLeft']) + ((xScale[iScroll][iFacet](d['rectRight']) - xScale[iScroll][iFacet](d['rectLeft']))/2) )
                  /*.attr('y', function(d){
                    if(barmode == 'overlay'){
                      return yScale[iScroll][iFacet](d['rectTop'])
                    }
                    else{
                      return yScale[iScroll][iFacet](d['rectTop']) + ((yScale[iScroll][iFacet](d['rectBottom']) - yScale[iScroll][iFacet](d['rectTop']))/2)
                    }
                  })*/
                  .attr('opacity', 1.0)
                  /*.attr('transform', function(d){
                   if(barmode=='overlay'){
                     return `rotate(-90, ${xScale[iScroll][iFacet](d['rectLeft']) + ((xScale[iScroll][iFacet](d['rectRight']) - xScale[iScroll][iFacet](d['rectLeft']))/2)}, ${yScale[iScroll][iFacet](d['rectTop'])})`
                   }
                   else{
                     return `rotate(-90, ${xScale[iScroll][iFacet](d['rectLeft']) + ((xScale[iScroll][iFacet](d['rectRight']) - xScale[iScroll][iFacet](d['rectLeft']))/2)}, ${yScale[iScroll][iFacet](d['rectTop']) + ((yScale[iScroll][iFacet](d['rectBottom']) - yScale[iScroll][iFacet](d['rectTop']))/2)})`
                   }
                 });*/

            }
            // <--- Add text to bars ---




            // --- Add Horizontal Lines from Variable --->
            if(hline.var != null){

                var g_bar_text = g_data.append('path')
                      .attr('class', function(d){
                        return 'hline_var group_' + domainGroup.map(d => d['group']).indexOf(d['group'])
                      })
                      .style('stroke-dasharray', function(d){
                        if(hline.var['line_style'] == 'dashed'){ return '5' }
                        else if(hline.var['line_style'] == 'dotted'){ return '2' }
                        else{ return '0' }
                      })
                      .attr('opacity', function(d){
                        if(d[hline.var['name']] != null){ return '1' }
                        else{ return '0' }
                      })
                      .attr('visibility', 'visible')
                      .attr('stroke', hline.var['clr'])
                      .attr('stroke-width', hline.var['width'])
                      .attr('d', function(d){return 'M ' +
                        xScale[iScroll][iFacet](d['x']) + ', ' +
                        yScale[iScroll][iFacet](d[hline.var['name']])
                        ' L ' +
                        xScale[iScroll][iFacet](d['rectRight']) + ', ' +
                        yScale[iScroll][iFacet](d[hline.var['name']])
                        ' Z'})

            }
            // <--- Add Vertical Lines from Variable ---






            // --- Add vertical lines from set values --->
            if(hline.value != null){
              svg.select('.g_scroll_' + iScroll).select('.facet_' + iFacet).selectAll('hline_path')
                  .data(hline.value)
                  .enter()
                  .append('path')
                    .style('stroke-dasharray', function(d){
                      if(d['line_style'] == 'dashed'){ return '5' }
                      else if(d['line_style'] == 'dotted'){ return '2' }
                      else{ return '0' }
                    })
                    .attr('d', function(d){
                      return 'M ' +
                      xScale[iScroll][iFacet].range()[0] + ', ' +
                      yScale[iScroll][iFacet](d['y']) +
                      ' L ' +
                      xScale[iScroll][iFacet].range()[1] + ', ' +
                      yScale[iScroll][iFacet](d['y']) +
                      ' Z'
                    })
                    .attr('stroke', d => d['clr'])
                    .attr('stroke-width',d => d['width'])
                    .attr('opacity', 0)
                    .attr('visibility', 'visible')
                    .transition()
                      .duration(800)
                      .attr('opacity', 1)
            }
            // <--- Add vertical lines from set values ---

        })

      })
    });







  // <---------------------
  // <----- BAR CHART -----
  // <---------------------










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
