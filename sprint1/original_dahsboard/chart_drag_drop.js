function chart_drag_drop(
  data,
  html_id,
  selected=false,

  data_plot=[
    {'index':0, 'group_var':null, 'clr_var':null, 'calculation':'#SUM(n)'},
    {'index':1, 'group_var':null, 'clr_var':null, 'calculation':'(#SUM(total_skillscore)*#SUM(n))/#SUM(n)'},
  ],

  values={var:null, size:18, weight:400, order:'as_appear', ascending:true},

  title={value:[{size:40, weight:700, text:null}, {size:32, weight:700, text:null}], line:false},

  clr={
    var:'clr',
    palette:null, // 'plotly', 'd3', 'g10', 't10', 'alphabet', 'dark24', 'light24', 'set1', 'pastel1'
    value:'#e32726'
  },

  font={family:'Catamaran'},

  margin={top:10, bottom:10, left:10, right:10, g:10},

  canvas={width:960}
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
            'dy': (iTextSplit*1.1) + 'em',
            'this-width-value': thisWidth,
            //'max-width-value': maxTextWidth
          })
        });

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










  // ------------------------>
  // ----- DATA DOMAINS ----->
  // ------------------------>

  var domainValues = [];

  var y_pos = (values.size*1.1);
  Array.from(new Set(data.map(d => d[values.var]))).forEach(function(v, i){

    var value_split = splitWrapText(v, (canvas.width - margin.left - margin.right), fontSize=values.size, fontWeight=values.weight, fontFamily=font.family);

    var text_width = 0;
    value_split.forEach(function(vSplit, iSplit){
      text_width += Math.max(text_width, textWidth(vSplit, values.size, values.weight, font.family))
    })

    domainValues.push({
      'include': true,
      'bucket_orig': i,
      'bucket': i,
      'value': v,
      'value_split': value_split,
      'text_width': text_width,
      'y_pos': y_pos,
      'rect_height': (value_split.length*(values.size*1.1)) + 6,
      'rect_width': text_width+6,
      'sort_var': (values.order != null && values.order != 'as_appear' && values.order != 'alphabetical')? data.filter(d => d[values.var] == v).map(d => d[values.order])[0]: null
    })

    y_pos += (value_split.length*(values.size*1.1)) + 6 + (values.size*1.1);
  })


  // Sort values
  if(values.order == 'alphabetical'){
    domainValues = domainValues.sort((a, b) => d3.ascending(a['group'], b['group']));
  }
  if(values.order != null && values.order != 'as_appear' && values.order != 'alphabetical'){
    domainValues = domainValues.sort((a, b) => d3.ascending(a['sort_var'], b['sort_var']));
  }
  if(!values.ascending){ domainValues.reverse(); }


  // Get colors for each value
  domainValues.forEach(function(v, i){
    if(clr.var != null){
      v['color'] = data.filter(d => d[values.var] == v['value']).map(d => d[clr.var])[0];
    }
    else if(clr.palette != null && palette_names.includes(clr.palette.toLowerCase())){
      v['color'] = palette[clr.palette][i];
    }
    else if(clr.value != null){
      v['color'] = clr.value;
    }
    else{
      v['color'] = 'white';
    }
  })
  //console.log('### domainValues', domainValues);

  // <------------------------
  // <----- DATA DOMAINS -----
  // <------------------------










  // ------------------------>
  // ----- GRAPH SIZING ----->
  // ------------------------>

  //var canvas.width = 960;
  if (canvas == undefined){
    var canvas = {width:960};
  }
  if(canvas.width == null){
    canvas.width = 960;
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
    height.title += (margin.g);
  }
  //console.log('title_ypos', title_ypos);
  //console.log('height.title', height.title);





  // Data Height
  height.data = (values.size*1.1);
  domainValues.forEach((v, i) => {
    height.data += (v['value_split'].length*(values.size*1.1)) + 6 + (values.size*1.1)
  });
  //console.log('height.data', height.data);





  // Canvas Height
  canvas.height = margin.top + height.title + height.data + margin.bottom;
  //console.log('canvas.height', canvas.height);




  domainValues.forEach(function(v, i){
    v['x_pos'] = (canvas.width - margin.left - margin.right)/2;
  })

  // <------------------------
  // <----- GRAPH SIZING -----
  // <------------------------











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





  // ----------------->
  // ----- TITLE ----->
  // ----------------->

  // Group
  var g_title = svg.append('g')
    .attr('class', "g_title")
    .attr('transform', `translate(${margin.left}, ${margin.top})`)
    .attr('selected', selected)
    .on('click', (event, v) => {

        if(event.currentTarget.getAttribute('selected') == 'false'){
          d3.selectAll('.g_title').transition().attr('selected', false);
          d3.selectAll('.title_rect').transition().duration(200).attr('opacity', 0.0);

          svg.selectAll('.g_title').transition().attr('selected', true);
          svg.selectAll('.title_rect').transition().duration(200).attr('opacity', 0.5);
          selected_filter = title.value[0].text;

          createSummaryData();
        }

    })
    .on('mouseover', function(d) {
        d3.select(this).style("cursor", "pointer");
    });


  //  Title Text
  if(title.value != null){

      g_title.append("rect")
        .attr('class', function(d, i){ return 'title_rect'})
        .attr('x', 0)
        .attr('y', 0)
        .attr('width', canvas.width - (margin.left + margin.right))
        .attr('height', height.title + height.data)
        .attr('stroke', '#d3d2d2')
        .attr('stroke-width', 3)
        .attr('fill', 'none')
        .attr('opacity', function(d){
          if(selected){ return 0.5 }
          else{ return 0.0 }
        });

      g_title.append("rect")
          .attr('class', function(d, i){ return 'title_rect'})
          .attr('x', 0)
          .attr('y', 0)
          .attr('width', canvas.width - (margin.left + margin.right))
          .attr('height', height.title - margin.g)
          .attr('fill', '#d3d2d2')
          .attr('opacity', function(d){
            if(selected){ return 0.5 }
            else{ return 0.0 }
          });

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
            .attr('stroke-width', '2');
      }
  }

  // <-----------------
  // <----- TITLE -----
  // <-----------------









  // --------------------------------->
  // ----- DRAG & DROP FUNCTIONS ----->
  // --------------------------------->

  function dragstarted(event, d) {
    d3.select(this).raise();

    d3.selectAll(".g_value_element").each(function(c) {
      if (c !== d) {
        //console.log('ORIGINAL c.y_pos:', c.y_pos)
      }
    })
  }


  function dragged(event, d) {
    var element = this;
    var this_rect_height = +element.getAttribute('rect_height');
    //var this_orig_x = element.getAttribute('x_orig');
    //var this_orig_y = element.getAttribute('y_orig');

    //d3.select(this).attr("x", d.x = event.x).attr("y", d.y = event.y);
    d3.select(this).attr("transform", `translate(${event.x}, ${event.y})`);

    svg.selectAll(".g_value_element").each(function(c) {
    if (c !== d) {
      if((event.y+(this_rect_height*0.5)) >= c.y_pos && (event.y+(this_rect_height*0.5)) <= (c.y_pos+c.rect_height)){
        d3.select(this).select(".value_rect").attr('stroke', 'black');
      }
      else {
        d3.select(this).select(".value_rect").attr('stroke', '#d3d2d2');
      }
    }
  });
  }


  function dragended(event, d) {
    var element = this;
    var this_value = element.getAttribute('value');
    var this_x_pos = +element.getAttribute('x_pos');
    var this_y_pos = +element.getAttribute('y_pos');
    var this_bucket = +element.getAttribute('bucket');
    var this_rect_height = +element.getAttribute('rect_height');
    var return_y = this_y_pos;

    var join = false;
    var split = false;
    var grouped = (domainValues.filter(d => d['bucket'] == this_bucket).length > 1)? true: false;
    var empty_buckets = [];


    svg.selectAll(".g_value_element").each(function(c) {
      if (c !== d) {
        d3.select(this).select(".value_rect").attr('stroke', '#d3d2d2');

        // --- JOIN: Change bucket value of dragged element --->
        if((event.y+(this_rect_height*0.5)) >= c.y_pos && (event.y+(this_rect_height*0.5)) <= (c.y_pos+c.rect_height)){
          //console.log('JOIN!!!')
          join = true;
          d3.select(element).attr('bucket', c.bucket);
          domainValues.filter(d => d['value'] == this_value).forEach(function(v, i){
            v['bucket'] = c.bucket;
          });
        }
      }
    })

    // --- SPLIT: Change bucket value to value of nearest empty bucket --->
    if(grouped & !join){
      var empty_buckets = [];
      for(let bucket = 0; bucket < domainValues.length; bucket++){
        if(!Array.from(new Set(domainValues.map(d => d['bucket']))).sort().includes(bucket)){
          empty_buckets.push(bucket)
        }
      }

      var closest_bucket;
      empty_buckets.every(function(vEmptyBucket, iEmptyBucket){
        if(domainValues.filter(d => d['value'] == this_value).map(d => d['bucket_orig'])[0] == vEmptyBucket){
          domainValues.filter(d => d['value'] == this_value).forEach(function(v, i){
            v['bucket'] = vEmptyBucket;
          });
          split = true;
          //console.log('SPLIT!!!')
          return;
        }
        else{
          if(closest_bucket == null){
            closest_bucket = vEmptyBucket;
          }
          else if(Math.abs(vEmptyBucket - domainValues.filter(d => d['value'] == this_value).map(d => d['bucket_orig'])[0]) < Math.abs(closest_bucket - domainValues.filter(d => d['value'] == this_value).map(d => d['bucket_orig'])[0])){
            closest_bucket = vEmptyBucket;
          }
        }
      });

      if(!split){
        domainValues.filter(d => d['value'] == this_value).forEach(function(v, i){
          v['bucket'] = closest_bucket;
        });
        split = true;
        //console.log('SPLIT!!!')
      }
    }


    if(join || split){
      // --- Change y-position of all elements --->
      var y_pos = (values.size*1.1);
      Array.from(new Set(domainValues.map(d => d['bucket']))).sort().forEach(function(vBucket, iBucket){

        domainValues.filter(d => d['bucket'] == vBucket).forEach(function(vValue, iValue){
          vValue['y_pos'] = y_pos;

          y_pos += (vValue['value_split'].length*(values.size*1.1)) + 7;
        });

        y_pos += (values.size*1.1);
      });

      domainValues.forEach(function(vValue, iValue){
        svg.selectAll(".g_value_element_" + iValue).transition().duration(100).attr("transform", `translate(${vValue['x_pos']}, ${vValue['y_pos']})`);
      })

      //console.log('domainValues:', domainValues)


      data.forEach(function(v,i){
        v['bucket'] = domainValues.filter(d => d['value'] == v['value']).map(d => d['bucket'])[0]
        v['include'] = domainValues.filter(d => d['value'] == v['value']).map(d => d['include'])[0]
      });

      //console.log('data:', data);

      createSummaryData();

    }
    else{
      domainValues.forEach(function(vValue, iValue){
        svg.selectAll(".g_value_element_" + iValue).transition().duration(100).attr("transform", `translate(${vValue['x_pos']}, ${vValue['y_pos']})`);
      })
    }


  }

  let dragdrop =d3.drag()
      .on("start", dragstarted)
      .on("drag", dragged)
      .on("end", dragended);

  // <---------------------------------
  // <----- DRAG & DROP FUNCTIONS -----
  // <---------------------------------



  // --------------------------------------------->
  // ----- DOUBLE-CLICK FUNCTION (Hide/Show) ----->
  // --------------------------------------------->

  function clicked(event, d) {
    if(event.defaultPrevented){ return; } // dragged

    var element = this;
    var changed_opacity = (+element.getAttribute('opacity') == 1.0)? 0.2: 1.0;

    d3.select(this).transition().duration(100).attr("opacity",changed_opacity);

    domainValues.filter(d => d['value'] == element.getAttribute('value')).forEach(function(vValue, iValue){
      vValue['include'] = (changed_opacity == 0.2)? false: true;
    });

    data.filter(d => d['value'] == element.getAttribute('value')).forEach(function(vValue, iValue){
      vValue['include'] = (changed_opacity == 0.2)? false: true;
    });

    dataPlot = [];
    Array.from(new Set(domainValues.filter(d => d['include'] == true).map(d => d['bucket']))).sort().forEach(function(vBucket, iBucket){
      newObs = {
        'yvar': null,
        'x': null,
        'clr': null
      };
      domainValues.filter(d => d['bucket'] == vBucket && d['include'] == true).forEach(function(vValue, iValue){

        dataObs = data.filter(d => d[values.var] == vValue['value'])[0];

        newObs['yvar'] = (newObs['yvar'] == null)? dataObs[values.var]: newObs['yvar'] + "<br>+ " + dataObs[values.var];
        newObs['x'] = (newObs['x'] == null)? dataObs['n']: newObs['x'] + dataObs['n'];
        if(newObs['clr'] == null){
          newObs['clr'] = dataObs['clr'];
        }

      })
      dataPlot.push(newObs)
    });

    //console.log('domainValues:', domainValues)
    //console.log('data:', data);

    createSummaryData();
    //changeGraph();

  }

  // <---------------------------------------------
  // <----- DOUBLE-CLICK FUNCTION (Hide/Show) -----
  // <---------------------------------------------





  // ----------------->
  // ----- CHART ----->
  // ----------------->

  // Group
  var g_chart = svg.append('g')
    .attr('class', 'g_chart')
    .attr('transform', `translate(${margin.left}, ${margin.top + height.title})`);



  var g_value_element = g_chart.selectAll()
  .data(domainValues)
  .enter()
  .append('g')
    .attr('class', (d, i) => 'g_value_element g_value_element_' + i)
    .attr('x_pos', d => d['x_pos'])
    .attr('y_pos', d => d['y_pos'])
    .attr('value', d => d['value'])
    .attr('bucket', d => d['bucket'])
    .attr('rect_height', d => d['rect_height'])
    .attr('opacity', 1.0)
    .attr('transform', (d) => `translate(${(canvas.width - margin.left - margin.right)/2}, ${d['y_pos']})`)
    .call(dragdrop)
    .on("dblclick", clicked)
    .on('mouseover', function(d) {
        d3.select(this).style("cursor", "pointer");
    });


  // --- Add gray rectangle --->
  g_value_element.append('rect')
    .attr('class', (d,  i) => 'value_rect value_rect_' + i)
    .attr('x', (d, i) => 0 - (d['text_width']/2) - 3)
    .attr('y', -3)
    .attr('width', d => d['text_width']+6)
    .attr('height', d => d['rect_height'])
    .attr('stroke', '#d3d2d2')
    .attr('fill', '#d3d2d2');



  // --- Add Text --->
  g_value_element.append('text')
      .attr('class', (d, i) => 'value_text value_text_' + i)
      .style('font-family', font.family)
      .style('font-size', values.size +  'px')
      .style('font-weight', values.weight)
      .style('text-anchor', 'middle')
      .style('dominant-baseline', 'hanging')
      .attr('x', 0)
      .attr('dy', function(d, i){ return i*1.1 + 'em' })
      //.attr('transform', `translate(${0}, ${vValue['y_pos']})`)
      .each(function(d, i){
        d3.select(this).selectAll('.switcher_text_' + i)
          .data(d['value_split'])
          .enter()
          .append('tspan')
          .attr('dy', (d2, i2) => i2*1.1 + 'em')
          .text( d => d)
      });
      //.text(d => d);


  /*
  domainValues.forEach(function(vValue, iValue){


      // --- Add Group --->
      var g_value = g_chart.append('g')
        .attr('class', 'g_value_' + iValue)
        .attr('transform', `translate(${0}, ${vValue['y_pos']})`);



      // --- Add Line --->
      g_value.append('path')
          .attr('d', 'M' + 0 + ',' + 0 + 'L' + (canvas.width - (margin.left + margin.right)) + ',' + 0)
          .attr('stroke', '#d3d2d2')
          .attr('stroke-width', '2');


      // --- Add group containing rectangle and text --->
      var g_value_element = g_value.append('g')
      .attr('class', 'g_value_element g_value_element' + iValue)
      .attr('x_orig', (canvas.width - margin.left - margin.right)/2)
      .attr('y_orig', (values.size*1.1)*0.5)
      .attr('transform', `translate(${(canvas.width - margin.left - margin.right)/2}, ${(values.size*1.1)*0.5})`)
      .call(dragdrop);


      // --- Add gray rectangle --->
      g_value_element.append('rect')
        .attr('class', 'value_rect value_rect_' + iValue)
        .attr('x', 0 - (vValue['text_width']/2) - 3)
        .attr('y', -3)
        .attr('width', d => vValue['text_width']+6)
        .attr('height', d => (vValue['value'].length*(values.size*1.1)) + 6)
        .attr('fill', '#d3d2d2');



      // --- Add Text --->
      g_value_element.selectAll('value_text_' + iValue)
          .data(vValue['value'])
          .enter()
          .append('text')
            .attr('class', 'value_text value_text_' + iValue)
            .style('font-family', font.family)
            .style('font-size', values.size +  'px')
            .style('font-weight', values.weight)
            .style('text-anchor', 'middle')
            .style('dominant-baseline', 'hanging')
            .attr('x_orig', 0)
            .attr('y_orig', 0)
            .attr('x', 0)
            .attr('dy', function(d, i){ return i*1.1 + 'em' })
            //.attr('transform', `translate(${0}, ${vValue['y_pos']})`)
            .text(d => d)
            //.call(dragdrop);


  });
  */


  // <-----------------
  // <----- CHART -----
  // <-----------------


}
