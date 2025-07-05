import React, { useState } from 'react';
import ReactDOM from 'react-dom';
import ChangePassword from './change_password';
import EditProfile from './edit_profile';

const AdminSettings = () => {
  const [activeSection, setActiveSection] = useState('editProfile');

  const handleSectionClick = (section) => {
    setActiveSection(section);
  };

  console.log('AdminSettings component loaded');

  return (
    <div className="admin-settings">
      <div className="settings-menu">
        <ul>
          <li
            className={activeSection === 'editProfile' ? 'active' : ''}
            onClick={() => handleSectionClick('editProfile')}
          >
            Edit Profile Information
          </li>
          <li
            className={activeSection === 'changePassword' ? 'active' : ''}
            onClick={() => handleSectionClick('changePassword')}
          >
            Change Password
          </li>
        </ul>
      </div>
      <div className="settings-content">
        {activeSection === 'editProfile' && <EditProfile />}
        {activeSection === 'changePassword' && <ChangePassword />}
      </div>
    </div>
  );
};

ReactDOM.render(<AdminSettings />, document.getElementById('admin-settings-root'));