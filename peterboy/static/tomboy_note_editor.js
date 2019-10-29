Vue.component('tomboy-note-editor', {
  name: 'tomboy-note-editor',
  props: ['content'],
  template: `
    <div>
      <div class="btn-toolbar mb-3" role="toolbar"> 
        <div class="btn-group mr-2" role="group"> 
          <button type="button" class="btn btn-secondary" @click.prevent="bold"><i class="fas fa-bold"></i></button>
          <button type="button" class="btn btn-secondary" @click.prevent="italic"><i class="fas fa-italic"></i></button>
          <button type="button" class="btn btn-secondary" @click.prevent="strike"><i class="fas fa-strikethrough"></i></button>
          <button type="button" class="btn btn-secondary" @click.prevent="highlight"><i class="fas fa-highlighter"></i></button>
          <button type="button" class="btn btn-secondary" @click.prevent="monospace"><i class="fab fa-medium-m"></i></button>         
        </div>
    
        <div class="dropdown mr-2"> 
          <button class="btn btn-secondary dropdown-toggle" type="button" id="dropdownMenuButton" data-toggle="dropdown">Font Size</button>
          <div class="dropdown-menu">
            <button class="dropdown-item" type="button" @click.prevent="small">작게</button>
            <button class="dropdown-item" type="button" @click.prevent="medium">보통</button>
            <button class="dropdown-item" type="button" @click.prevent="large">크게</button>
            <button class="dropdown-item" type="button" @click.prevent="xxlarge">아주크게</button> 
          </div>
        </div>
      
        <div class="btn-group mr-2" role="group">
          <button type="button" class="btn btn-secondary" @click.prevent="list_insert"><i class="fas fa-list"></i></button>
          <button type="button" class="btn btn-secondary" @click.prevent="list_indent"><i class="fas fa-indent"></i></button>
          <button type="button" class="btn btn-secondary" @click.prevent="list_outdent"><i class="fas fa-outdent"></i></button>
        </div>
        
        <button type="button" class="btn btn-secondary" @click.prevent="link_insert"><i class="fas fa-link"></i></button>
      </div>
      
      <!-- Modal -->
      <div class="modal fade" id="linkModal" tabindex="-1" role="dialog">
        <div class="modal-dialog modal-dialog-centered" role="document">
          <div class="modal-content">
            <div class="modal-header">
              <h5 class="modal-title" id="linkModalTitle">링크 타입을 선택하세요</h5>
              <button type="button" class="close" data-dismiss="modal" aria-label="Close">
                <span aria-hidden="true">&times;</span>
              </button>
            </div>
            <div class="modal-footer">
              <div class="container-fluid">
                <button type="button" class="btn btn-primary" @click.prevent="link_type($event, 'note')">쪽지 링크</button>
                <button type="button" class="btn btn-secondary" @click.prevent="link_type($event, 'url')">URL 링크</button>
              </div>
            </div>
          </div>
        </div>
      </div>  
      
      <div ref="editor" contenteditable style="border: solid 2px grey; height: 400px;" v-html="content">
      </div>
    </div>
  `,
  methods: {
    bold: function () {
      document.execCommand('StyleWithCSS', false, null);
      document.execCommand('bold', false, '');
    },
    italic: function () {
      document.execCommand('StyleWithCSS', false, null);
      document.execCommand('italic', false, '');
    },
    strike: function () {
      document.execCommand('StyleWithCSS', false, null);
      document.execCommand('strikeThrough', false, '');
    },
    highlight: function () {
      document.execCommand('StyleWithCSS', false, null);
      document.execCommand('hiliteColor', false, 'yellow');
    },
    monospace: function () {
      document.execCommand('StyleWithCSS', false, null);
      document.execCommand('fontName', false, 'monospace');
    },
    small: function () {
      document.execCommand('StyleWithCSS', false, null);
      document.execCommand('fontSize', false, '2');
    },
    medium: function () {
      document.execCommand('StyleWithCSS', false, null);
      document.execCommand('fontSize', false, '3');
    },
    large: function () {
      document.execCommand('StyleWithCSS', false, null);
      document.execCommand('fontSize', false, '4');
    },
    xxlarge: function () {
      document.execCommand('StyleWithCSS', false, null);
      document.execCommand('fontSize', false, '6');
    },
    list_insert: function () {
      document.execCommand('insertUnorderedList', false);
    },
    list_indent: function () {
      document.execCommand('indent', false);
    },
    list_outdent: function () {
      document.execCommand('outdent', false);
    },
    link_insert: function () {
      $('#linkModal').modal({keyboard: false})
      $('#linkModal').modal('show')
    },
    link_type: function (e, type_) {
      document.execCommand('copy', false)

      navigator.clipboard.readText().then(
        function(clipText) {
          if (type_ === 'note') {
            document.execCommand('createLink', false, '#' + clipText)
          } else if (type_ === 'url') {
            document.execCommand('createLink', false, clipText)
          }

          $('#linkModal').modal('hide')
        }
      )
    },
    getHtml: function () {
      return this.$refs.editor.innerHTML
    }
  }
})