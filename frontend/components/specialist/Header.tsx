type SpecialistHeaderProps = {
  displayName: string;
  specialization: string;
};

export function Header({ displayName, specialization }: SpecialistHeaderProps) {
  return (
    <header id="specialist-sticky-header" className="specialist-header" aria-label="Specialist profile header">
      <div className="specialist-header__inner container">
        <div className="specialist-header__identity">
          <p className="specialist-header__display-name">{displayName}</p>
          <p className="specialist-header__specialization">{specialization}</p>
        </div>
      </div>
    </header>
  );
}

export default Header;
