/* global notify */
import React from 'react';
import { FormControl, FormGroup, Overlay, Popover, Row, Col } from 'react-bootstrap';
import Button from '../../components/Button';
const $ = window.$ = require('jquery');

const propTypes = {
  defaultLabel: React.PropTypes.string,
  sql: React.PropTypes.string,
  schema: React.PropTypes.string,
  dbId: React.PropTypes.number,
  animation: React.PropTypes.bool,
};
const defaultProps = {
  defaultLabel: 'Undefined',
  animation: true,
};

class SaveQuery extends React.PureComponent {
  constructor(props) {
    super(props);
    this.state = {
      description: '',
      label: props.defaultLabel,
      showSave: false,
    };
    this.toggleSave = this.toggleSave.bind(this);
    this.onSave = this.onSave.bind(this);
    this.onCancel = this.onCancel.bind(this);
    this.onLabelChange = this.onLabelChange.bind(this);
    this.onDescriptionChange = this.onDescriptionChange.bind(this);
  }
  onSave() {
    const url = '/savedqueryviewapi/api/create';
    const data = {
      label: this.state.label,
      description: this.state.description,
      db_id: this.props.dbId,
      schema: this.props.schema,
      sql: this.props.sql,
      csrf_token: $('input#csrf_token').val(),
    };
    $.ajax({
      type: 'POST',
      url,
      data,
      success: () => notify.success('The query was saved'),
      error: e => notify.error(`The query couldn't be saved. \n${e}`),
      dataType: 'json',
    });
    this.setState({ showSave: false });
  }
  onCancel() {
    this.setState({ showSave: false });
  }
  onLabelChange(e) {
    this.setState({ label: e.target.value });
  }
  onDescriptionChange(e) {
    this.setState({ description: e.target.value });
  }
  renderPopover() {
    return (
      <Popover id="embed-code-popover">
        <FormGroup bsSize="small" style={{ width: '350px' }}>
          <Row>
            <Col md={12}>
              <small>
                <label className="control-label" htmlFor="embed-height">
                  Label
                </label>
              </small>
              <FormControl
                type="text"
                placeholder="Label for your query"
                value={this.state.label}
                onChange={this.onLabelChange}
              />
            </Col>
          </Row>
          <br />
          <Row>
            <Col md={12}>
              <small>
                <label className="control-label" htmlFor="embed-height">Description</label>
              </small>
              <FormControl
                componentClass="textarea"
                placeholder="textarea"
                value={this.state.description}
                onChange={this.onDescriptionChange}
              />
            </Col>
          </Row>
          <br />
          <Row>
            <Col md={12}>
              <Button
                bsStyle="primary"
                onClick={this.onSave}
                className="m-r-3"
              >
                Save
              </Button>
              <Button onClick={this.onCancel} className="cancelQuery">
                Cancel
              </Button>
            </Col>
          </Row>
        </FormGroup>
      </Popover>
    );
  }
  toggleSave(e) {
    this.setState({ target: e.target, showSave: !this.state.showSave });
  }
  render() {
    return (
      <span className="SaveQuery">
        <Overlay
          trigger="click"
          target={this.state.target}
          show={this.state.showSave}
          placement="bottom"
          animation={this.props.animation}
        >
          {this.renderPopover()}
        </Overlay>
        <Button bsSize="small" className="toggleSave" onClick={this.toggleSave}>
          <i className="fa fa-save" /> Save
        </Button>
      </span>
    );
  }
}
SaveQuery.propTypes = propTypes;
SaveQuery.defaultProps = defaultProps;

export default SaveQuery;
