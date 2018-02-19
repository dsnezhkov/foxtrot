from pygments.style import Style
from pygments.token import Token
from pygments.styles.default import DefaultStyle


class AgentStyle(Style):

    styles = {
        Token.Menu.Completions.Completion.Current: 'bg:#00aaaa #000000',
        Token.Menu.Completions.Completion: 'bg:#008888 #ffffff',
        Token.Menu.Completions.ProgressButton: 'bg:#003333',
        Token.Menu.Completions.ProgressBar: 'bg:#00aaaa',

        # User input.
        Token:          '#ffffcc',
        Token.Toolbar:  '#ffffff bg:#000000',

        # Prompt.
        Token.Username: '#884444',
        Token.At:       '#00aa00',
        Token.Marker:   '#00aa00',
        Token.Host:     '#008888',
        Token.DTime:    '#884444 underline',
    }
    styles.update(DefaultStyle.styles)


